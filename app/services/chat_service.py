from app.agent.agent import Agent

class ChatService:
    def __init__(self) -> None:
        self.agent =Agent()

    async def chat(self, message: str) -> str:
        response = await self.agent.chat(message)
        return response
