from typing import Any


class PermissionManager:
    """Controls which CodeMind tools can execute."""

    SAFE_TOOLS = {
        "read_file",
        "search_files",
        "search_content",
        "list_files",
        "list_folder",
        "chat",
    }

    RISKY_TOOLS = {
        "create_file",
        "write_file",
        "delete_file",
        "create_folder",
        "delete_folder",
        "run_command",
    }

    BLOCKED_TOOLS = {
        "format_disk",
        "delete_workspace",
    }

    def check_plan(
        self,
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify plan steps as safe, approval-required, or blocked."""

        if not isinstance(plan, dict):
            raise ValueError("Plan must be a dictionary.")

        steps = plan.get("steps")

        if not isinstance(steps, list):
            raise ValueError("'steps' must be a list.")

        pending_approvals = []
        safe_steps = []
        blocked_steps = []

        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError(
                    f"Step {index} must be an object."
                )

            tool = step.get("tool")
            arguments = step.get("arguments")
            risk = step.get("risk")

            if not isinstance(tool, str) or not tool.strip():
                raise ValueError(
                    f"Invalid tool in step {index}."
                )

            tool = tool.strip()

            if not isinstance(arguments, dict):
                raise ValueError(
                    f"Invalid arguments in step {index}."
                )

            if risk not in {"safe", "risky"}:
                raise ValueError(
                    f"Invalid risk level in step {index}."
                )

            # Blocked tools can never be approved through this manager.
            if tool in self.BLOCKED_TOOLS:
                blocked_steps.append({
                    "step_index": index,
                    "tool": tool,
                    "status": "blocked",
                })
                continue

            # Unknown tools fail closed.
            if (
                tool not in self.SAFE_TOOLS
                and tool not in self.RISKY_TOOLS
            ):
                blocked_steps.append({
                    "step_index": index,
                    "tool": tool,
                    "status": "unknown_tool_blocked",
                })
                continue

            # The tool policy takes priority over the model's decision.
            # A safe tool marked risky still requires approval.
            is_risky = (
                tool in self.RISKY_TOOLS
                or risk == "risky"
            )

            if is_risky:
                pending_approvals.append({
                    "step_index": index,
                    "tool": tool,
                    "arguments": arguments,
                    "status": "approval_required",
                })
            else:
                safe_steps.append({
                    "step_index": index,
                    "tool": tool,
                    "arguments": arguments,
                    "status": "safe",
                })

        return {
            "approved_to_execute": (
                len(pending_approvals) == 0
                and len(blocked_steps) == 0
            ),
            "safe_steps": safe_steps,
            "pending_approvals": pending_approvals,
            "blocked_steps": blocked_steps,
        }