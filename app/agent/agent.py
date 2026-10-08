from app.llm.ollama_client import OllamaClient

class Agent:
    def __init__(self)-> None:
        self.llm = OllamaClient()

    async def chat(self,message:str)-> str:
        prompt =f"""
            You are CodeMind, an AI coding assistant.
            User message:
            {message}
            Give a clear and useful answer.
            """
        response = await self.llm.chat(prompt)
        return response