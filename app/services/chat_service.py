from pathlib import Path
from typing import Any

from app.agent.agent import Agent


class ChatService:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def _get_agent(self, workspace: str) -> Agent:
        workspace_path = Path(workspace).expanduser().resolve()

        if not workspace_path.exists():
            raise ValueError("Workspace folder does not exist.")

        if not workspace_path.is_dir():
            raise ValueError("Workspace must be a directory.")

        workspace_key = str(workspace_path)

        if workspace_key not in self._agents:
            self._agents[workspace_key] = Agent(
                workspace=workspace_key
            )

        return self._agents[workspace_key]

    @staticmethod
    def _format_result(
        result: dict[str, Any],
        default_message: str,
    ) -> dict[str, Any]:
        """Ensure every API response contains a response string."""

        formatted = dict(result)

        response = formatted.get("response")

        # Prefer an existing, non-empty response.
        if isinstance(response, str) and response.strip():
            formatted["response"] = response.strip()
            return formatted

        # Extract text returned by executed tools.
        messages: list[str] = []

        results = formatted.get("results", [])

        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue

                tool_result = item.get("result")

                if isinstance(tool_result, str):
                    if tool_result.strip():
                        messages.append(tool_result.strip())

                elif isinstance(tool_result, dict):
                    for key in ("response", "message", "output"):
                        value = tool_result.get(key)

                        if isinstance(value, str) and value.strip():
                            messages.append(value.strip())
                            break

        # Remove duplicate messages while preserving order.
        messages = list(dict.fromkeys(messages))

        if messages:
            formatted["response"] = "\n\n".join(messages)
        else:
            status = formatted.get("status", "completed")

            if status == "approval_required":
                formatted["response"] = (
                    "This action requires your approval before execution."
                )
            elif status == "blocked":
                formatted["response"] = (
                    "The requested action was blocked by the permission system."
                )
            elif status in ("denied", "cancelled"):
                formatted["response"] = (
                    "The planned actions were cancelled."
                )
            elif status == "failed":
                formatted["response"] = (
                    "The task failed. Check the execution results for details."
                )
            else:
                formatted["response"] = default_message

        return formatted

    async def chat(
        self,
        message: str,
        workspace: str,
    ) -> dict[str, Any]:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        agent = self._get_agent(workspace)
        result = await agent.run(message)

        return self._format_result(
            result,
            "The task completed, but no response text was returned.",
        )

    async def approve(
        self,
        approval_id: str,
        workspace: str,
    ) -> dict[str, Any]:
        if not approval_id.strip():
            raise ValueError("Approval ID cannot be empty.")

        agent = self._get_agent(workspace)
        result = await agent.approve(approval_id)

        return self._format_result(
            result,
            "The approval request was processed. Check the execution results.",
        )

    async def deny(
        self,
        approval_id: str,
        workspace: str,
    ) -> dict[str, Any]:
        if not approval_id.strip():
            raise ValueError("Approval ID cannot be empty.")

        agent = self._get_agent(workspace)
        result = await agent.deny(approval_id)

        return self._format_result(
            result,
            "The planned actions were cancelled.",
        )