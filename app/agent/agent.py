from typing import Any
from uuid import uuid4
from app.llm.ollama_client import OllamaClient
from app.agent.planner import Planner
from app.agent.permission_manager import PermissionManager
from app.tools.terminal_tool import TerminalTool
from app.tools.file_tool import FileTool
from app.tools.folder_tool import FolderTool
from app.tools.search_tool import SearchTool


class Agent:
    """CodeMind agent: planning, permission checks, and tool execution."""

    def __init__(self, workspace: str) -> None:
        self.llm = OllamaClient()
        self.planner = Planner()
        self.permission_manager = PermissionManager()

        self.terminal_tool = TerminalTool(workspace)
        self.file_tool = FileTool(workspace)
        self.folder_tool = FolderTool(workspace)
        self.search_tool = SearchTool(workspace)

        # Temporary in-memory approval storage.
        self.pending_runs: dict[str, dict[str, Any]] = {}

    async def chat(self, message: str) -> str:
        """Answer a general question without workspace operations."""

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        prompt = f"""
You are CodeMind, an AI coding assistant.
Give a clear, useful, and accurate answer.

User message:
{message}
"""
        return await self.llm.chat(prompt)

    async def run(self, message: str) -> dict[str, Any]:
        """Plan an action, check permissions, and execute when permitted."""

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        # 1. Ask the planner to create a plan.
        plan = await self.planner.create_plan(message)

        if not isinstance(plan, dict):
            raise ValueError("Planner must return a dictionary.")

        steps = plan.get("steps")

        if not isinstance(steps, list) or not steps:
            raise ValueError("Plan must contain a non-empty steps list.")

        # 2. Check every planned action.
        permission = self.permission_manager.check_plan(plan)

        # 3. Reject the entire plan if any step is blocked.
        if permission["blocked_steps"]:
            return {
                "intent": plan.get("intent"),
                "status": "blocked",
                "blocked_steps": permission["blocked_steps"],
            }

        # 4. If ANY action is risky, ask approval before executing
        # ANY step. This preserves the original step order and prevents
        # safe steps from being lost in a mixed plan.
        if permission["pending_approvals"]:
            approval_id = str(uuid4())

            self.pending_runs[approval_id] = {
                "plan": plan,
                "original_message": message,
                "pending_approvals": permission["pending_approvals"],
            }

            return {
                "intent": plan.get("intent"),
                "status": "approval_required",
                "approval_id": approval_id,
                "pending_approvals": permission["pending_approvals"],
                "message": (
                    "This plan contains risky actions. "
                    "No steps have been executed yet."
                ),
            }

        # 5. No risky actions: execute safe steps in plan order.
        return await self._execute_steps(
            steps=steps,
            original_message=message,
            intent=plan.get("intent"),
        )

    async def approve(self, approval_id: str) -> dict[str, Any]:
        """Execute the original plan after explicit user approval."""

        pending = self.pending_runs.get(approval_id)

        if pending is None:
            raise ValueError(
                "Invalid or already processed approval ID."
            )

        plan = pending["plan"]
        message = pending["original_message"]
        steps = plan.get("steps")

        if not isinstance(steps, list) or not steps:
            raise ValueError("Stored plan is invalid.")

        # Recheck the entire plan against current security rules.
        permission = self.permission_manager.check_plan(plan)

        if permission["blocked_steps"]:
            self.pending_runs.pop(approval_id, None)

            return {
                "intent": plan.get("intent"),
                "status": "blocked",
                "blocked_steps": permission["blocked_steps"],
                "results": [],
            }

        # Ensure the risky actions still match the actions that
        # the user originally approved.
        approved_indices = {
            step.get("step_index")
            for step in pending["pending_approvals"]
        }

        current_risky_indices = {
            step.get("step_index")
            for step in permission["pending_approvals"]
        }

        if approved_indices != current_risky_indices:
            self.pending_runs.pop(approval_id, None)

            return {
                "intent": plan.get("intent"),
                "status": "approval_invalidated",
                "message": (
                    "The pending actions changed. "
                    "Please submit the request again."
                ),
                "results": [],
            }

        # Consume approval before executing to prevent replay.
        self.pending_runs.pop(approval_id, None)

        # Execute the complete plan in its original order.
        return await self._execute_steps(
            steps=steps,
            original_message=message,
            intent=plan.get("intent"),
        )

    async def deny(self, approval_id: str) -> dict[str, Any]:
        """Cancel a pending plan without executing any of its steps."""

        pending = self.pending_runs.pop(approval_id, None)

        if pending is None:
            raise ValueError(
                "Invalid or already processed approval ID."
            )

        return {
            "intent": pending["plan"].get("intent"),
            "status": "denied",
            "message": "Pending actions were cancelled. Nothing was executed.",
            "cancelled_actions": [
                {
                    "tool": step.get("tool"),
                    "step_index": step.get("step_index"),
                }
                for step in pending["pending_approvals"]
            ],
        }

    async def _execute_steps(
        self,
        steps: list[dict[str, Any]],
        original_message: str,
        intent: Any,
    ) -> dict[str, Any]:
        """Execute steps in order and stop if a step fails."""

        results: list[dict[str, Any]] = []

        for index, step in enumerate(steps):
            try:
                output = await self._execute_step(
                    step=step,
                    original_message=original_message,
                )

                # TerminalTool may report failure or timeout
                # as a returned result instead of raising an exception.
                tool_status = (
                    output.get("status")
                    if isinstance(output, dict)
                    else None
                )

                if tool_status in {"failed", "timeout"}:
                    results.append({
                        "tool": step.get("tool"),
                        "step_index": index,
                        "status": tool_status,
                        "result": output,
                    })

                    return {
                        "intent": intent,
                        "status": "failed",
                        "failed_step": index,
                        "results": results,
                    }

                results.append({
                    "tool": step.get("tool"),
                    "step_index": index,
                    "status": "success",
                    "result": output,
                })

            except Exception as exc:
                results.append({
                    "tool": step.get("tool"),
                    "step_index": index,
                    "status": "error",
                    "error": str(exc),
                })

                # Do not continue a multi-step plan after an error.
                return {
                    "intent": intent,
                    "status": "failed",
                    "failed_step": index,
                    "results": results,
                }

        return {
            "intent": intent,
            "status": "completed",
            "results": results,
        }

    async def _execute_step(
        self,
        step: dict[str, Any],
        original_message: str,
    ) -> Any:
        """Dispatch a validated plan step to its tool."""

        if not isinstance(step, dict):
            raise ValueError("Plan step must be a dictionary.")

        tool = step.get("tool")
        arguments = step.get("arguments", {})

        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a dictionary.")

        # -------------------------
        # Terminal tool
        # -------------------------
        if tool == "run_command":
            command = arguments.get("command")
            cwd = arguments.get("cwd", ".")
            timeout = arguments.get("timeout", 30)

            return await self.terminal_tool.run_command(
                command=command,
                cwd=cwd,
                timeout=timeout,
            )

        # -------------------------
        # Search tools
        # -------------------------
        if tool == "search_files":
            query = arguments.get("query", "")
            extension = arguments.get("extension", "")
            folder_path = arguments.get("folder_path", ".")
            limit = arguments.get("limit", 50)

            if not isinstance(query, str):
                raise ValueError("search_files query must be a string.")

            if not isinstance(extension, str):
                raise ValueError(
                    "search_files extension must be a string."
                )

            return self.search_tool.search_files(
                query=query,
                extension=extension,
                folder_path=folder_path,
                limit=limit,
            )

        if tool == "search_content":
            query = arguments.get("query")
            folder_path = arguments.get("folder_path", ".")
            limit = arguments.get("limit", 50)

            if not isinstance(query, str) or not query.strip():
                raise ValueError(
                    "search_content requires a valid query."
                )

            return self.search_tool.search_content(
                query=query,
                folder_path=folder_path,
                limit=limit,
            )

        # -------------------------
        # File tools
        # -------------------------
        if tool == "list_files":
            return self.file_tool.list_files()

        if tool == "read_file":
            file_path = arguments.get("file_path")

            if not isinstance(file_path, str) or not file_path.strip():
                raise ValueError("read_file requires a file_path.")

            return self.file_tool.read_file(file_path)

        if tool == "create_file":
            file_path = arguments.get("file_path")

            if not isinstance(file_path, str) or not file_path.strip():
                raise ValueError("create_file requires a file_path.")

            return self.file_tool.create_file(file_path)

        if tool == "write_file":
            file_path = arguments.get("file_path")
            content = arguments.get("content")

            if not isinstance(file_path, str) or not file_path.strip():
                raise ValueError("write_file requires a file_path.")

            if not isinstance(content, str):
                raise ValueError("write_file requires string content.")

            return self.file_tool.write_file(file_path, content)

        if tool == "delete_file":
            file_path = arguments.get("file_path")

            if not isinstance(file_path, str) or not file_path.strip():
                raise ValueError("delete_file requires a file_path.")

            return self.file_tool.delete_file(file_path)

        # -------------------------
        # Folder tools
        # -------------------------
        if tool == "create_folder":
            folder_path = arguments.get("folder_path")

            if (
                not isinstance(folder_path, str)
                or not folder_path.strip()
            ):
                raise ValueError(
                    "create_folder requires a folder_path."
                )

            return self.folder_tool.create_folder(folder_path)

        if tool == "list_folder":
            folder_path = arguments.get("folder_path", ".")

            if (
                not isinstance(folder_path, str)
                or not folder_path.strip()
            ):
                raise ValueError(
                    "list_folder requires a valid folder_path."
                )

            return self.folder_tool.list_folder(folder_path)

        if tool == "delete_folder":
            folder_path = arguments.get("folder_path")

            if (
                not isinstance(folder_path, str)
                or not folder_path.strip()
            ):
                raise ValueError(
                    "delete_folder requires a folder_path."
                )

            return self.folder_tool.delete_folder(folder_path)

        # -------------------------
        # LLM chat tool
        # -------------------------
        if tool == "chat":
            prompt = arguments.get("message", original_message)

            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("chat requires a valid message.")

            return await self.llm.chat(prompt)

        raise ValueError(f"Unsupported tool: {tool}")