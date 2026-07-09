"""Research endpoints — launch and view deep-dive sessions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.research import Research
from app.schemas.common import StatusResponse

router = APIRouter(prefix="/research", tags=["research"])


# --- schemas ---
class ResearchCreate(BaseModel):
    query: str


class ResearchOut(BaseModel):
    id: str
    query: str
    status: str
    findings: str | None
    sources: str | None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}


def _to_out(r: Research) -> ResearchOut:
    return ResearchOut(
        id=r.id,
        query=r.query,
        status=r.status,
        findings=r.findings,
        sources=r.sources,
        created_at=str(r.created_at) if r.created_at else None,
        updated_at=str(r.updated_at) if r.updated_at else None,
    )


# --- routes ---
@router.post("", response_model=ResearchOut)
async def create_research(
    body: ResearchCreate, db: Session = Depends(get_db)
) -> ResearchOut:
    """Start a new research session.

    Creates the record as 'pending', then kicks off the research agent
    in the background. The frontend polls or listens on /ws/status for completion.
    """
    research = Research(query=body.query, status="pending")
    db.add(research)
    db.commit()
    db.refresh(research)

    # Fire-and-forget: run the research agent in the background.
    import asyncio

    asyncio.create_task(_run_research(research.id, body.query))

    return _to_out(research)


@router.get("", response_model=list[ResearchOut])
def list_research(db: Session = Depends(get_db)) -> list[ResearchOut]:
    stmt = select(Research).order_by(Research.created_at.desc())
    rows = db.execute(stmt).scalars().all()
    return [_to_out(r) for r in rows]


@router.get("/{research_id}", response_model=ResearchOut)
def get_research(research_id: str, db: Session = Depends(get_db)) -> ResearchOut:
    r = db.get(Research, research_id)
    if not r:
        raise HTTPException(status_code=404, detail="research session not found")
    return _to_out(r)


@router.delete("/{research_id}", response_model=StatusResponse)
def delete_research(
    research_id: str, db: Session = Depends(get_db)
) -> StatusResponse:
    r = db.get(Research, research_id)
    if not r:
        raise HTTPException(status_code=404, detail="research session not found")
    db.delete(r)
    db.commit()
    return StatusResponse(detail="deleted")


# --- background research agent ---
async def _run_research(research_id: str, query: str) -> None:
    """Background research agent.

    Uses the active LLM provider to run a research-style query and stores
    the findings. Best-effort: failure sets status='failed' without crashing.
    """
    from app.core.logging import get_logger
    from app.db.session import SessionLocal
    from app.services.providers.base import ChatMessage
    from app.services.providers.registry import registry

    logger = get_logger(__name__)

    db = SessionLocal()
    try:
        record = db.get(Research, research_id)
        if not record:
            return
        record.status = "running"
        db.commit()

        # Broadcast status update to frontend
        try:
            from app.ws import manager

            await manager.broadcast("status", {
                "type": "research",
                "id": research_id,
                "status": "running",
            })
        except Exception:
            pass

        provider = registry.get()
        system_prompt = (
            "You are a thorough research assistant. Given a research query, "
            "provide a comprehensive analysis with structured findings. "
            "Format your response in Markdown. Include section headers, "
            "key findings, and cite any reasoning or sources. "
            "Be detailed but concise."
        )
        messages = [ChatMessage(role="user", content=query)]
        reply = await provider.chat(
            messages, system_prompt=system_prompt
        )
        if isinstance(reply, ChatMessage):
            reply = reply.content or ""

        record.findings = reply
        record.status = "done"
        db.commit()

        # Persist a compact research summary into the memory store so it can
        # be surfaced by chat recall and the memory view (GET /memory?kind=research).
        try:
            from app.services.memory.service import MemoryService

            research_summary = f"Research: {query}\n\n{reply[:4000]}"
            await MemoryService(db).add(
                content=research_summary,
                namespace="research",
                kind="research",
                user_id=record.user_id,
            )
        except Exception as mem_exc:
            logger.error(
                "Failed to persist research memory for %s: %s",
                research_id, mem_exc,
            )

        try:
            from app.ws import manager

            await manager.broadcast("status", {
                "type": "research",
                "id": research_id,
                "status": "done",
            })
        except Exception:
            pass

    except Exception as exc:
        logger.error("Research %s failed: %s", research_id, exc)
        try:
            record = db.get(Research, research_id)
            if record:
                record.status = "failed"
                record.findings = f"Research failed: {exc}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
