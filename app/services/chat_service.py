from app.llm.ollama_client import OllamaClient

class ChatService:
    def __init__(self) -> None:
        self.ollama = OllamaClient()

    async def chat(self, message: str) -> str:
        response = await self.ollama.chat(message)
        return response
