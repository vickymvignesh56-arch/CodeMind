from pathlib import Path
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

    async def chat(self, message: str, workspace: str) -> str:
        if not message.strip():
            raise ValueError("Message cannot be empty.")
        agent = self._get_agent(workspace)
        response = await agent.chat(message)
        return response