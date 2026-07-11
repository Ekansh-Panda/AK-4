"""Tool approval endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.schemas.common import StatusResponse
from app.services.tools.approval import resolve_approval, get_pending_calls

router = APIRouter(prefix="/tools", tags=["tools"])

class ToolApprovalRequest(BaseModel):
    tool_call_id: str

@router.get("/pending", response_model=list[str])
def list_pending(user_id: str = Depends(get_current_user)) -> list[str]:
    """List all currently pending tool_call_ids waiting for approval."""
    return get_pending_calls()

@router.post("/approve", response_model=StatusResponse)
def approve_tool(req: ToolApprovalRequest, user_id: str = Depends(get_current_user)) -> StatusResponse:
    """Approve a pending tool call."""
    if resolve_approval(req.tool_call_id, True):
        return StatusResponse(detail="approved")
    raise HTTPException(status_code=404, detail="Pending tool call not found or already resolved.")

@router.post("/reject", response_model=StatusResponse)
def reject_tool(req: ToolApprovalRequest, user_id: str = Depends(get_current_user)) -> StatusResponse:
    """Reject a pending tool call."""
    if resolve_approval(req.tool_call_id, False):
        return StatusResponse(detail="rejected")
    raise HTTPException(status_code=404, detail="Pending tool call not found or already resolved.")
