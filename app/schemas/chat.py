from pydantic import BaseModel,Field
class ChatRequest(BaseModel):
    message:str
    workspace: str = Field(min_length=1)

class ChatResponse(BaseModel):
    response: str