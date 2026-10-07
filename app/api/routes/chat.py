from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(
    tags=['chat']
)

chat_service=ChatService()

@router.post('/chat',response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = await chat_service.chat(request.message)
    return ChatResponse(response=response)