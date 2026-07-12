"""Plan CRUD endpoints + step approval."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.plan import PlanStep, TaskPlan
from app.schemas.common import StatusResponse
from app.schemas.plan import PlanCreate, PlanDetail, PlanOut, PlanStepOut, SubPlanCreate
from app.services.tools.approval import register_pending_approval
from app.ws import manager

router = APIRouter(prefix="/plans", tags=["plans"])


_PLAN_STATUSES = {"pending", "running", "completed", "failed", "cancelled", "rejected"}
_STEP_STATUSES = {"pending", "running", "completed", "failed", "pending_approval", "rejected"}


def _validate_status(value: str, allowed: set[str]) -> str:
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status: {value}")
    return value


async def _broadcast(event: str, payload: dict) -> None:
    await manager.broadcast("status", {"type": event, **payload})


# --- Plan CRUD ---


@router.post("", response_model=PlanOut)
async def create_plan(
    body: PlanCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanOut:
    plan = TaskPlan(
        user_id=user_id,
        device_id="local",
        goal=body.goal,
        trust_level=body.trust_level,
        parallel=body.parallel,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    if body.steps:
        order = 0
        for s in body.steps:
            args = s.args_json if isinstance(s.args_json, str) else json.dumps(s.args_json or {})
            step = PlanStep(
                plan_id=plan.id,
                parent_step_id=s.parent_step_id,
                step_order=s.step_order or order,
                action=s.action,
                args_json=args,
            )
            db.add(step)
            order += 1
        db.commit()

    await _broadcast("plan_created", {"plan_id": plan.id, "goal": plan.goal})
    return PlanOut.model_validate(plan)


@router.get("", response_model=list[PlanOut])
def list_plans(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlanOut]:
    rows = db.execute(
        select(TaskPlan).where(TaskPlan.user_id == user_id).order_by(desc(TaskPlan.created_at))
    ).scalars().all()
    return [PlanOut.model_validate(r) for r in rows]


@router.get("/{plan_id}", response_model=PlanDetail)
def get_plan(
    plan_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanDetail:
    plan = db.get(TaskPlan, plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(status_code=404, detail="plan not found")
    steps = db.execute(
        select(PlanStep).where(PlanStep.plan_id == plan_id).order_by(PlanStep.step_order)
    ).scalars().all()
    return PlanDetail(
        **PlanOut.model_validate(plan).model_dump(),
        steps=[PlanStepOut.model_validate(s) for s in steps],
    )


@router.post("/{plan_id}/cancel", response_model=PlanOut)
async def cancel_plan(
    plan_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanOut:
    plan = db.get(TaskPlan, plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(status_code=404, detail="plan not found")
    plan.status = _validate_status("cancelled", _PLAN_STATUSES)
    plan.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(plan)
    await _broadcast("plan_cancelled", {"plan_id": plan.id})
    return PlanOut.model_validate(plan)


# --- Step actions ---


@router.post("/{plan_id}/steps/{step_id}/approve", response_model=StatusResponse)
async def approve_step(
    plan_id: str,
    step_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    plan = db.get(TaskPlan, plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(status_code=404, detail="plan not found")
    step = db.get(PlanStep, step_id)
    if not step or step.plan_id != plan_id:
        raise HTTPException(status_code=404, detail="step not found")
    if step.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Step is not pending approval (status={step.status})")

    step.status = "running"
    db.commit()
    await _broadcast("step_started", {"plan_id": plan_id, "step_id": step_id})
    return StatusResponse(detail="approved")


@router.post("/{plan_id}/steps/{step_id}/retry", response_model=PlanStepOut)
async def retry_step(
    plan_id: str,
    step_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanStepOut:
    plan = db.get(TaskPlan, plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(status_code=404, detail="plan not found")
    step = db.get(PlanStep, step_id)
    if not step or step.plan_id != plan_id:
        raise HTTPException(status_code=404, detail="step not found")

    step.status = "pending_approval" if plan.trust_level != "god" else "running"
    step.retries += 1
    step.error = None
    db.commit()
    db.refresh(step)
    await _broadcast("step_approval_needed", {"plan_id": plan_id, "step_id": step_id, "action": step.action})
    return PlanStepOut.model_validate(step)


# --- Sub-plans ---


@router.post("/{plan_id}/subplans", response_model=PlanOut)
async def create_subplan(
    plan_id: str,
    body: SubPlanCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanOut:
    plan = db.get(TaskPlan, plan_id)
    if not plan or plan.user_id != user_id:
        raise HTTPException(status_code=404, detail="plan not found")
    parent_step = db.get(PlanStep, body.parent_step_id)
    if not parent_step or parent_step.plan_id != plan_id:
        raise HTTPException(status_code=404, detail="parent step not found")

    sub = TaskPlan(
        user_id=user_id,
        device_id=plan.device_id,
        goal=body.goal,
        trust_level=body.trust_level or plan.trust_level,
        parallel=False,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    parent_step.args_json = json.dumps({"sub_plan_id": sub.id})
    db.commit()

    await _broadcast("subplan_created", {"plan_id": plan.id, "sub_plan_id": sub.id, "parent_step_id": body.parent_step_id})
    return PlanOut.model_validate(sub)
