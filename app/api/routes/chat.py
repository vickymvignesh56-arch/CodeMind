from typing import Any
from fastapi import APIRouter, HTTPException
from app.schemas.chat import (
    ApprovalRequest,
    ChatRequest,
    ChatResponse,
)
from app.services.chat_service import ChatService


router = APIRouter(tags=["chat"])
chat_service = ChatService()


def build_response(result: dict[str, Any]) -> ChatResponse:
    status = result.get("status", "completed")

    messages = {
        "approval_required": (
            "Approval required. No actions have been executed."
        ),
        "completed": "Task completed successfully.",
        "denied": "Request denied. No pending actions were executed.",
        "blocked": "Request blocked by security rules.",
        "failed": "Task failed. Check the results for details.",
        "approval_invalidated": (
            "Approval is no longer valid. Submit the request again."
        ),
    }
    return ChatResponse(
        response=result.get("message") or messages.get(
            status, f"Task status: {status}"
        ),
        status=status,
        intent=result.get("intent"),
        approval_id=result.get("approval_id"),
        pending_approvals=result.get("pending_approvals", []),
        results=result.get("results", []),
        blocked_steps=result.get("blocked_steps", []),
        cancelled_actions=result.get("cancelled_actions", []),
        failed_step=result.get("failed_step"),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await chat_service.chat(
            message=request.message,
            workspace=request.workspace,
        )
        return build_response(result)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/chat/approve", response_model=ChatResponse)
async def approve(request: ApprovalRequest) -> ChatResponse:
    try:
        result = await chat_service.approve(
            approval_id=request.approval_id,
            workspace=request.workspace,
        )
        return build_response(result)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/chat/deny", response_model=ChatResponse)
async def deny(request: ApprovalRequest) -> ChatResponse:
    try:
        result = await chat_service.deny(
            approval_id=request.approval_id,
            workspace=request.workspace,
        )
        return build_response(result)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc