"""ExecutorService — runs TaskPlan steps with approval, replan, parallel batches."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import COMPUTER_USE_PLAN_TIMEOUT_S, get_effective_bool
from app.core.logging import get_logger
from app.models.plan import PlanStep, TaskPlan
from app.services.providers.base import ChatMessage
from app.services.providers.registry import ProviderRegistry
from app.services.tools.approval import register_pending_approval
from app.services.tools.base import Tool
from app.services.tools.registry import ToolRegistry
from app.ws import manager

logger = get_logger(__name__)

_CRITICAL_ACTIONS = {
    "install",
    "exec",
    "execute_shell",
    "commit",
    "deploy",
    "fs_delete",
    "process_kill",
    "service_stop",
}


class ExecutorService:
    def __init__(
        self,
        db: Session,
        providers: ProviderRegistry,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._db = db
        self._providers = providers
        self._tool_registry = tool_registry

    async def execute_plan(self, plan_id: str) -> None:
        plan = self._db.get(TaskPlan, plan_id)
        if not plan:
            logger.error("Plan %s not found", plan_id)
            return

        plan.status = "running"
        plan.error = None
        plan.completed_at = None
        self._db.commit()
        await manager.broadcast("status", {"type": "plan_started", "plan_id": plan.id})

        steps = list(
            self._db.execute(
                select(PlanStep)
                .where(PlanStep.plan_id == plan_id)
                .order_by(PlanStep.step_order)
            )
            .scalars()
            .all()
        )

        try:
            await asyncio.wait_for(
                self._run_plan(plan, steps),
                timeout=COMPUTER_USE_PLAN_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            plan.status = "cancelled"
            plan.error = f"Plan timed out after {COMPUTER_USE_PLAN_TIMEOUT_S}s"
            plan.completed_at = datetime.now(timezone.utc)
            self._db.commit()
            await manager.broadcast(
                "status", {"type": "plan_cancelled", "plan_id": plan.id, "reason": "timeout"}
            )
            return
        except asyncio.CancelledError:
            plan.status = "cancelled"
            plan.completed_at = datetime.now(timezone.utc)
            self._db.commit()
            await manager.broadcast(
                "status", {"type": "plan_cancelled", "plan_id": plan.id, "reason": "cancelled"}
            )
            return

        final_status = plan.status
        plan.completed_at = datetime.now(timezone.utc)
        self._db.commit()
        await manager.broadcast(
            "status", {"type": f"plan_{final_status}", "plan_id": plan.id}
        )

    async def _run_plan(self, plan: TaskPlan, steps: list[PlanStep]) -> None:
        if plan.parallel and steps:
            batches = self._topological_batches(steps)
            for batch in batches:
                await asyncio.gather(
                    *[self._execute_step(plan, step) for step in batch],
                    return_exceptions=True,
                )
        else:
            for step in steps:
                await self._execute_step(plan, step)
                if plan.status in ("failed", "cancelled", "rejected"):
                    break

        if plan.status not in ("failed", "cancelled", "rejected"):
            any_failed = any(s.status == "failed" for s in steps)
            plan.status = "completed" if not any_failed else "failed"

    def _topological_batches(self, steps: list[PlanStep]) -> list[list[PlanStep]]:
        batches: list[list[PlanStep]] = []
        current: list[PlanStep] = []
        last_order = None
        for step in steps:
            if last_order is not None and step.step_order != last_order:
                if current:
                    batches.append(current)
                    current = []
            current.append(step)
            last_order = step.step_order
        if current:
            batches.append(current)
        return batches

    async def _execute_step(self, plan: TaskPlan, step: PlanStep) -> None:
        step.status = "running"
        self._db.commit()
        await manager.broadcast(
            "status",
            {"type": "step_started", "plan_id": plan.id, "step_id": step.id},
        )

        needs_approval = (
            plan.trust_level != "god"
            and getattr(step, "requires_approval", True)
        )

        if needs_approval:
            step.status = "pending_approval"
            self._db.commit()
            await manager.broadcast(
                "status",
                {"type": "step_approval_needed", "plan_id": plan.id, "step_id": step.id, "action": step.action},
            )
            future = register_pending_approval(step.id)
            try:
                approved = await asyncio.wait_for(future, timeout=COMPUTER_USE_PLAN_TIMEOUT_S)
            except asyncio.TimeoutError:
                step.status = "rejected"
                step.error = "Approval timed out"
                plan.status = "cancelled"
                self._db.commit()
                return
            if not approved:
                step.status = "rejected"
                step.error = "Approval rejected"
                plan.status = "rejected"
                self._db.commit()
                return
            step.status = "running"
            self._db.commit()

        max_retries = 2
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                result = await self._run_step(plan, step)
                step.result = result if isinstance(result, str) else json.dumps(result, default=str)
                step.status = "completed"
                step.completed_at = datetime.now(timezone.utc)
                step.error = None
                self._db.commit()
                await manager.broadcast(
                    "status",
                    {"type": "step_completed", "plan_id": plan.id, "step_id": step.id},
                )

                if get_effective_bool(self._db, "computer_use_double_verify", True):
                    if step.action in _CRITICAL_ACTIONS:
                        await self._verify_step(plan, step)
                return
            except Exception as exc:  # noqa: BLE001
                logger.error("Step %s failed (attempt %d): %s", step.id, attempt + 1, exc, exc_info=True)
                last_error = str(exc)
                step.retries = attempt + 1
                step.error = last_error
                self._db.commit()

                if attempt < max_retries:
                    new_args = await self._replan_args(plan, step, last_error)
                    if new_args is not None:
                        step.args_json = json.dumps(new_args, default=str)
                        step.status = "running"
                        self._db.commit()
                        await manager.broadcast(
                            "status",
                            {
                                "type": "step_started",
                                "plan_id": plan.id,
                                "step_id": step.id,
                                "action": step.action,
                                "replan": True,
                            },
                        )
                        continue

                step.status = "failed"
                self._db.commit()
                await manager.broadcast(
                    "status",
                    {"type": "step_failed", "plan_id": plan.id, "step_id": step.id, "error": last_error},
                )
                plan.status = "failed"
                plan.error = last_error
                self._db.commit()
                return

        step.status = "failed"
        step.error = last_error
        plan.status = "failed"
        plan.error = last_error
        self._db.commit()

    async def _run_step(self, plan: TaskPlan, step: PlanStep) -> Any:
        args: dict[str, Any] = {}
        if step.args_json:
            try:
                parsed = json.loads(step.args_json)
                if isinstance(parsed, dict):
                    args = parsed
            except (json.JSONDecodeError, TypeError):
                args = {}

        if self._tool_registry is not None:
            tool = self._tool_registry.get(step.action)
            if tool is not None:
                if asyncio.iscoroutinefunction(getattr(tool, "run", None)):
                    return await tool.run(**args)
                return await asyncio.to_thread(tool.run, **args)

        raise ValueError(f"No tool registered for action '{step.action}'")

    async def _replan_args(self, plan: TaskPlan, step: PlanStep, error: str) -> dict[str, Any] | None:
        provider = self._providers.get()
        try:
            step_args: dict[str, Any] = {}
            if step.args_json:
                try:
                    step_args = json.loads(step.args_json)
                    if not isinstance(step_args, dict):
                        step_args = {}
                except (json.JSONDecodeError, TypeError):
                    step_args = {}

            messages = [
                ChatMessage(
                    role="system",
                    content="You are a replanner. Given a failed tool action, return adjusted JSON args as a compact JSON object, or null if no adjustment is possible.",
                ),
                ChatMessage(
                    role="user",
                    content=json.dumps({
                        "action": step.action,
                        "args": step_args,
                        "error": error,
                        "plan_goal": plan.goal,
                    }),
                ),
            ]
            response = await provider.chat(messages)
            content = response.content if isinstance(response, ChatMessage) else str(response)
            parsed = json.loads(content) if content else None
            if isinstance(parsed, dict):
                return parsed
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Replan failed for step %s: %s", step.id, exc)
            return None

    async def _verify_step(self, plan: TaskPlan, step: PlanStep) -> None:
        provider = self._providers.get()
        try:
            messages = [
                ChatMessage(
                    role="system",
                    content="Verify the following tool execution result. Reply with 'ok' or 'fail' followed by a brief reason.",
                ),
                ChatMessage(
                    role="user",
                    content=json.dumps({
                        "action": step.action,
                        "result": step.result,
                        "plan_goal": plan.goal,
                    }),
                ),
            ]
            response = await provider.chat(messages)
            verdict = response.content if isinstance(response, ChatMessage) else str(response)
            logger.info("Double-verify for step %s: %s", step.id, verdict)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Double-verify failed for step %s: %s", step.id, exc)
