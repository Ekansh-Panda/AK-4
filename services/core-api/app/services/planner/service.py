"""PlannerService — decomposes a goal into PlanStep objects via an LLM.

Handles parallel sub-plan grouping, double-verification for critical steps,
and structured tool args (list-of-args, never raw shell strings).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_effective_bool, settings
from app.core.logging import get_logger
from app.models.plan import PlanStep, TaskPlan
from app.services.providers.base import ChatMessage
from app.services.providers.registry import ProviderRegistry
from app.ws import manager

logger = get_logger(__name__)

_DOUBLE_VERIFY_KEY = "computer_use_double_verify"

_CRITICAL_ACTIONS = {"install", "exec", "commit", "deploy", "fs_write", "fs_delete"}

_SYSTEM_PROMPT = """\
You are a deterministic task planner for an autonomous computer-control agent.

Your only job is to decompose an arbitrary user goal into a sequence of atomic,
machine-readable plan steps. Every step must be concrete, executable, and safe
for a Python backend to run without additional interpretation.

## OUTPUT FORMAT

Return a single JSON object with a top-level "steps" array. No markdown fences,
no prose, no explanation.

```json
{
  "steps": [
    {
      "action": "shell",
      "args": {"command": ["apt-get", "install", "-y", "python3"]},
      "description": "Install python3 via apt"
    }
  ]
}
```

## RULES

1. Each step has exactly three keys:
   - "action": one of the registered tool names (e.g. "shell", "fs_write",
     "fs_read", "browser", "install", "exec", "commit", "deploy").
   - "args": a JSON object with structured arguments for that tool.
   - "description": human-readable summary of what the step does.
2. Shell commands MUST be "command": list[str]. Never a raw string. Never
   shell=True style. Compound commands MUST be split into sequential steps.
3. Every step MUST be atomic. One logical action per step.
4. If the goal is mutable (installs software, writes files, starts services,
   commits code, deploys), the step immediately after it MUST be a "verify"
   step that checks the expected outcome using the same structured format.
5. If a step cannot be expressed with the available tools, use "shell" with
   the minimal exact command needed.
"""

_PARALLEL_SYSTEM_PROMPT = """\
You are a deterministic task planner for an autonomous computer-control agent
that supports parallel execution.

Your job is to decompose the user goal into fully independent sub-plans that
can run concurrently. Each sub-plan is a self-contained ordered list of steps.

## OUTPUT FORMAT

Return a single JSON object with a top-level "sub_plans" array. No markdown
fences, no prose, no explanation.

```json
{
  "sub_plans": [
    {
      "description": "Install python3",
      "steps": [
        {
          "action": "install",
          "args": {"package": "python3", "manager": "apt"},
          "description": "Install python3 via apt"
        },
        {
          "action": "verify",
          "args": {"check": "python3 --version"},
          "description": "Verify python3 installed"
        }
      ]
    }
  ]
}
```

## RULES

1. Each sub-plan is fully independent and can run concurrently with the others.
2. Steps within a sub-plan are ordered (sequential execution).
3. Each step has "action", "args", and "description".
4. Shell commands are "command": list[str] — never raw strings.
5. Every mutable action (install, exec, commit, deploy, fs_write, fs_delete)
   MUST be followed by a "verify" step that checks the expected outcome.
6. Keep the output minimal: only the JSON object described above.
"""


def _broadcast(event: str, payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast("status", {"type": event, **payload}))
    except RuntimeError:
        pass


def _goal_to_fallback_command(goal: str) -> list[str]:
    parts = [p.strip() for p in goal.replace(",", " ").split() if p.strip()]
    return parts or ["echo", goal]


def _parse_response(response: str | ChatMessage) -> list[dict]:
    if isinstance(response, ChatMessage):
        content = (response.content or "").strip()
    else:
        content = str(response).strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) > 1:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("LLM response was not valid JSON, using fallback step")
        return _fallback_step()

    if "sub_plans" in parsed:
        sub_plans = parsed["sub_plans"]
        if isinstance(sub_plans, list) and sub_plans:
            flat: list[dict] = []
            for sub in sub_plans:
                steps = sub.get("steps", [])
                if isinstance(steps, list):
                    flat.extend(steps)
            if flat:
                return flat
            return _fallback_step()
        return _fallback_step()

    steps = parsed.get("steps", [])
    if isinstance(steps, list) and steps:
        return steps

    logger.warning("Plan missing steps array, using fallback step")
    return _fallback_step()


def _fallback_step() -> list[dict]:
    return [
        {
            "action": "shell",
            "args": {"command": ["echo", "(fallback) no steps generated by planner"]},
            "description": "Fallback no-op step",
        }
    ]


class PlannerService:
    """Decomposes goals into TaskPlan + PlanStep rows using an LLM."""

    def __init__(self, db: Session, providers: ProviderRegistry) -> None:
        self._db = db
        self._providers = providers

    async def plan(
        self,
        goal: str,
        *,
        user_id: str = "",
        device_id: str = "",
        parallel: bool = False,
        trust_level: str = "manual",
    ) -> TaskPlan:
        logger.info("Planning goal: %s (parallel=%s, trust=%s)", goal, parallel, trust_level)

        double_verify = get_effective_bool(
            self._db, _DOUBLE_VERIFY_KEY, settings.COMPUTER_USE_DOUBLE_VERIFY
        )

        plan = TaskPlan(
            user_id=user_id,
            device_id=device_id,
            goal=goal,
            trust_level=trust_level,
            parallel=parallel,
            status="pending",
        )
        self._db.add(plan)
        self._db.commit()
        self._db.refresh(plan)

        await _broadcast("plan_created", {
            "plan_id": plan.id,
            "goal": goal,
            "parallel": parallel,
            "trust_level": trust_level,
        })

        plan.status = "running"
        self._db.commit()
        await _broadcast("plan_started", {
            "plan_id": plan.id,
        })

        try:
            steps = await self._generate_steps(goal, parallel)
            self._persist_steps(plan.id, steps, parallel, double_verify)

            plan.status = "completed"
            plan.completed_at = datetime.now(timezone.utc)
            self._db.commit()

            await _broadcast("plan_completed", {
                "plan_id": plan.id,
                "step_count": len(steps),
            })

        except Exception as exc:
            logger.error("Planning failed for goal %s: %s", goal, exc)
            plan.status = "failed"
            plan.error = str(exc)
            plan.completed_at = datetime.now(timezone.utc)
            self._db.commit()
            await _broadcast("plan_failed", {
                "plan_id": plan.id,
                "error": str(exc),
            })
            raise

        return plan

    async def _generate_steps(self, goal: str, parallel: bool) -> list[dict]:
        provider = self._providers.get()
        system_prompt = _PARALLEL_SYSTEM_PROMPT if parallel else _SYSTEM_PROMPT
        user_prompt = (
            f'Goal: "{goal}"\n\n'
            "Return the plan as a single JSON object only. "
            "No markdown fences, no prose, no explanation."
        )

        try:
            response = await provider.chat(
                [ChatMessage(role="user", content=user_prompt)],
                system_prompt=system_prompt,
            )
        except Exception as exc:
            logger.warning("LLM plan generation failed, using fallback: %s", exc)
            return [
                {
                    "action": "shell",
                    "args": {"command": _goal_to_fallback_command(goal)},
                    "description": goal,
                }
            ]

        return _parse_response(response)

    def _persist_steps(
        self,
        plan_id: str,
        steps: list[dict],
        parallel: bool,
        double_verify: bool,
    ) -> list[PlanStep]:
        if not steps:
            steps = _fallback_step()

        db_steps: list[PlanStep] = []
        step_order = 0

        for raw in steps:
            action = str(raw.get("action", "shell"))
            args = raw.get("args", {})
            description = str(raw.get("description", ""))

            if not isinstance(args, dict):
                args = {}

            step = PlanStep(
                plan_id=plan_id,
                step_order=step_order,
                action=action,
                args_json=json.dumps(args),
                status="pending",
            )
            db_steps.append(step)
            step_order += 1

            if double_verify and action in _CRITICAL_ACTIONS:
                verify = PlanStep(
                    plan_id=plan_id,
                    parent_step_id=None,
                    step_order=step_order,
                    action="verify",
                    args_json=json.dumps({
                        "after_action": action,
                        "check": description,
                    }),
                    status="pending",
                )
                db_steps.append(verify)
                step_order += 1

                try:
                    coro = manager.broadcast("status", {
                        "type": "verification_attached",
                        "plan_id": plan_id,
                        "after_action": action,
                        "description": description,
                    })
                    asyncio.get_running_loop().create_task(coro)
                except RuntimeError:
                    pass

        self._db.add_all(db_steps)
        self._db.commit()
        for s in db_steps:
            self._db.refresh(s)

        return db_steps
