
import asyncio

from app.llm.ollama_client import OllamaClient


async def main():
    client = OllamaClient()
    response = await client.chat(
        "Write a simple Python hello world function."
    )
    print("\nOllama Response:\n")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
