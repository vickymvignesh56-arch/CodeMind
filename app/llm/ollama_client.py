import httpx
from app.core.config import settings
class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def chat(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        timeout = httpx.Timeout( connect=10.0, read=300.0, write=10.0, pool=10.0, )
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        return data["response"]
