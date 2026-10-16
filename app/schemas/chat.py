from typing import Any
from pydantic import BaseModel, Field
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    workspace: str = Field(min_length=1)
class ApprovalRequest(BaseModel):
    approval_id: str = Field(min_length=1)
    workspace: str = Field(min_length=1)
class ChatResponse(BaseModel):
    response: str
    status: str = "completed"
    intent: Any = None

    approval_id: str | None = None
    pending_approvals: list[dict[str, Any]] = Field(
        default_factory=list
    )

    results: list[dict[str, Any]] = Field(
        default_factory=list
    )
    blocked_steps: list[dict[str, Any]] = Field(
        default_factory=list
    )
    cancelled_actions: list[dict[str, Any]] = Field(
        default_factory=list
    )

    failed_step: int | None = None