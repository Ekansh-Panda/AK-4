"""ChatService — orchestrates persona + provider + persistence for a turn.

Shared by the REST chat router and the /ws/chat WebSocket so both paths use the
same history, persona prompt and provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.message import Message
from app.models.session import ChatSession
from app.services.persona.service import DEFAULT_MODE, PersonaService
from app.services.providers.base import ChatMessage
from app.services.providers.registry import ProviderRegistry
from app.services.providers.registry import registry as provider_registry
from app.services.tools.registry import registry as tool_registry

logger = get_logger(__name__)

# Summarize a session after every N assistant turns (cheap, best-effort).
SUMMARIZE_EVERY = 10


class ChatService:
    def __init__(
        self,
        db: Session,
        *,
        providers: ProviderRegistry | None = None,
        persona: PersonaService | None = None,
    ) -> None:
        self._db = db
        self._providers = providers or provider_registry
        self._persona = persona or PersonaService()

    # --- sessions ---
    def get_or_create_session(
        self,
        session_id: str | None,
        *,
        persona_mode: str | None = None,
        user_id: str | None = None,
    ) -> ChatSession:
        if session_id:
            existing = self._db.get(ChatSession, session_id)
            # Only reuse a session the caller owns (None owner = legacy/shared).
            if existing and (
                existing.user_id is None
                or user_id is None
                or existing.user_id == user_id
            ):
                return existing
        session = ChatSession(
            persona_mode=PersonaService.normalize_mode(persona_mode),
            user_id=user_id,
        )
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def get_owned_session(
        self, session_id: str, user_id: str | None
    ) -> ChatSession | None:
        """Return the session only if owned by ``user_id`` (else None)."""
        session = self._db.get(ChatSession, session_id)
        if session is None:
            return None
        if session.user_id is not None and user_id is not None and session.user_id != user_id:
            return None
        return session

    def history(self, session_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
        )
        return list(self._db.execute(stmt).scalars().all())

    def _persist(self, session_id: str, role: str, content: str, model: str | None = None) -> Message:
        msg = Message(session_id=session_id, role=role, content=content, model=model)
        self._db.add(msg)
        self._db.commit()
        self._db.refresh(msg)
        return msg

    def _build_provider_messages(self, session_id: str) -> list[ChatMessage]:
        # History already includes the just-persisted user message — do not
        # append it again (that caused a duplicate user turn).
        return [
            ChatMessage(role=m.role, content=m.content)
            for m in self.history(session_id)
        ]

    def _resolve_mode(self, session: ChatSession, persona_mode: str | None) -> str:
        """Per-session persona mode. If a valid override is passed, persist it."""
        if persona_mode and PersonaService.is_valid_mode(persona_mode):
            if session.persona_mode != persona_mode:
                session.persona_mode = persona_mode
                self._db.commit()
            return persona_mode
        return PersonaService.normalize_mode(session.persona_mode)

    # --- turns ---
    async def respond(
        self,
        *,
        session_id: str | None,
        user_text: str,
        model: str | None = None,
        persona_mode: str | None = None,
        user_id: str | None = None,
    ) -> tuple[ChatSession, Message]:
        """Single-shot turn: persist user msg, get reply, persist + return it."""
        session = self.get_or_create_session(
            session_id, persona_mode=persona_mode, user_id=user_id
        )
        mode = self._resolve_mode(session, persona_mode)
        self._persist(session.id, "user", user_text)
        provider = self._providers.get()
        msgs = self._build_provider_messages(session.id)
        system_prompt = self._persona.build_prompt(
            mode, context=await self._recall_context(user_text, user_id)
        )
        try:
            import json
            from app.core.config import get_effective_bool
            from app.services.settings_service import AGENT_MODE_KEY

            agent_mode = get_effective_bool(self._db, AGENT_MODE_KEY, True)
            tool_schemas = tool_registry.schemas() if agent_mode else []
            
            while True:
                reply_or_msg = await provider.chat(
                    msgs, model=model, system_prompt=system_prompt, tools=tool_schemas
                )
                
                if isinstance(reply_or_msg, ChatMessage):
                    msgs.append(reply_or_msg)
                    if reply_or_msg.tool_calls:
                        for tc in reply_or_msg.tool_calls:
                            tool_name = tc.get("function", {}).get("name")
                            args_str = tc.get("function", {}).get("arguments", "{}")
                            try:
                                args = json.loads(args_str)
                            except json.JSONDecodeError:
                                args = {}
                            
                            tool = tool_registry.get(tool_name)
                            if tool:
                                if getattr(tool, "requires_approval", False) and tc.get("id"):
                                    from app.services.tools.approval import register_pending_approval
                                    from app.ws import manager
                                    tc_id = tc["id"]
                                    await manager.broadcast("status", {
                                        "type": "tool_approval",
                                        "tool_call_id": tc_id,
                                        "tool_name": tool_name,
                                        "args": args
                                    })
                                    future = register_pending_approval(tc_id)
                                    try:
                                        approved = await future
                                    except asyncio.CancelledError:
                                        approved = False
                                        
                                    if not approved:
                                        res = f"Tool {tool_name} execution was REJECTED by the user."
                                    else:
                                        import asyncio
                                        if asyncio.iscoroutinefunction(tool.run):
                                            res = await tool.run(**args)
                                        else:
                                            res = tool.run(**args)
                                else:
                                    import asyncio
                                    if asyncio.iscoroutinefunction(tool.run):
                                        res = await tool.run(**args)
                                    else:
                                        res = tool.run(**args)
                            else:
                                res = f"Tool {tool_name} not found."
                            
                            msgs.append(ChatMessage(role="tool", content=str(res), tool_call_id=tc.get("id")))
                        continue # loop again
                    else:
                        reply_text = reply_or_msg.content or ""
                        break
                else:
                    reply_text = reply_or_msg
                    break
                    
        except Exception as exc:  # noqa: BLE001 - fall back to mock on failure
            logger.warning("Provider %s chat failed, using mock: %s", provider.name, exc)
            provider = self._providers.get("mock")
            reply_text = await provider.chat(msgs, system_prompt=system_prompt)
        
        reply = self._persist(session.id, "assistant", reply_text, model=provider.name)
        await self._store_facts(user_text, user_id)
        await self._maybe_summarize(session.id)
        return session, reply

    async def stream_response(
        self,
        *,
        session_id: str | None,
        user_text: str,
        model: str | None = None,
        persona_mode: str | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[tuple[str, str]]:
        """Yield ('session', session_id) once, then ('token', chunk) repeatedly.

        Persists the user message up front and the full assistant message at the
        end.
        """
        session = self.get_or_create_session(
            session_id, persona_mode=persona_mode, user_id=user_id
        )
        mode = self._resolve_mode(session, persona_mode)
        self._persist(session.id, "user", user_text)
        yield ("session", session.id)

        provider = self._providers.get()
        msgs = self._build_provider_messages(session.id)
        system_prompt = self._persona.build_prompt(
            mode, context=await self._recall_context(user_text, user_id)
        )
        chunks: list[str] = []
        try:
            import json
            from app.core.config import get_effective_bool
            from app.services.settings_service import AGENT_MODE_KEY

            agent_mode = get_effective_bool(self._db, AGENT_MODE_KEY, True)
            tool_schemas = tool_registry.schemas() if agent_mode else []
            
            while True:
                tool_call_occurred = False
                async for chunk in provider.stream(
                    msgs, model=model, system_prompt=system_prompt, tools=tool_schemas
                ):
                    if isinstance(chunk, ChatMessage):
                        msgs.append(chunk)
                        if chunk.tool_calls:
                            for tc in chunk.tool_calls:
                                tool_name = tc.get("function", {}).get("name")
                                args_str = tc.get("function", {}).get("arguments", "{}")
                                try:
                                    args = json.loads(args_str)
                                except json.JSONDecodeError:
                                    args = {}
                                    
                                tool = tool_registry.get(tool_name)
                                if tool:
                                    if getattr(tool, "requires_approval", False) and tc.get("id"):
                                        from app.services.tools.approval import register_pending_approval
                                        from app.ws import manager
                                        tc_id = tc["id"]
                                        await manager.broadcast("status", {
                                            "type": "tool_approval",
                                            "tool_call_id": tc_id,
                                            "tool_name": tool_name,
                                            "args": args
                                        })
                                        future = register_pending_approval(tc_id)
                                        try:
                                            approved = await future
                                        except asyncio.CancelledError:
                                            approved = False
                                            
                                        if not approved:
                                            res = f"Tool {tool_name} execution was REJECTED by the user."
                                        else:
                                            import asyncio
                                            if asyncio.iscoroutinefunction(tool.run):
                                                res = await tool.run(**args)
                                            else:
                                                res = tool.run(**args)
                                    else:
                                        import asyncio
                                        if asyncio.iscoroutinefunction(tool.run):
                                            res = await tool.run(**args)
                                        else:
                                            res = tool.run(**args)
                                else:
                                    res = f"Tool {tool_name} not found."
                                
                                msgs.append(ChatMessage(role="tool", content=str(res), tool_call_id=tc.get("id")))
                            tool_call_occurred = True
                            break # restart the stream loop
                    else:
                        chunks.append(chunk)
                        yield ("token", chunk)
                
                if not tool_call_occurred:
                    break
                    
        except Exception as exc:  # noqa: BLE001 - degrade to mock mid-failure
            logger.warning(
                "Provider %s stream failed, using mock: %s", provider.name, exc
            )
            # Only fall back cleanly if nothing was streamed yet.
            if not chunks:
                provider = self._providers.get("mock")
                async for chunk in provider.stream(msgs, system_prompt=system_prompt):
                    if isinstance(chunk, str):
                        chunks.append(chunk)
                        yield ("token", chunk)
            else:
                yield ("error", f"provider error: {exc}")

        self._persist(
            session.id, "assistant", "".join(chunks).strip(), model=provider.name
        )
        await self._store_facts(user_text, user_id)
        await self._maybe_summarize(session.id)
        yield ("done", session.id)

    # --- memory recall + fact capture (Phase 2.2) ---
    async def _recall_context(self, user_text: str, user_id: str | None) -> str | None:
        """Build a 'Relevant context' block from recalled facts + summaries.

        Best-effort: returns None on any error or when nothing is found, so chat
        never breaks because of memory.
        """
        try:
            from app.services.memory.service import MemoryService
            from app.services.files.service import FileIngestionService

            mem = MemoryService(self._db)
            files = FileIngestionService(self._db)
            
            facts = await mem.search(user_text, namespace="user:facts", limit=5)
            file_results = files.search(user_text, limit=5)
            summaries = mem.list(kind="summary", limit=3)
            
            lines = [f"- {m.content}" for m in facts]
            lines += [f"- [file excerpt] {chunk.content}" for chunk, score in file_results]
            lines += [f"- (earlier) {m.content}" for m in summaries]
            if not lines:
                return None
            return "Relevant context (use it only if helpful):\n" + "\n".join(lines)
        except Exception as exc:  # noqa: BLE001 - non-blocking
            logger.debug("recall skipped: %s", exc)
            return None

    @staticmethod
    def _extract_facts(text: str) -> list[str]:
        """Cheap heuristic fact extraction from a user turn (max 3)."""
        import re

        patterns = [
            (r"\bmy name is ([A-Z][\w'\-]{1,40})", "User's name is {0}."),
            (r"\bi(?:'m| am) (?:a |an )?([\w '\-]{3,50})", "User is {0}."),
            (r"\bi (?:like|love|enjoy) ([\w '\-]{3,50})", "User likes {0}."),
            (r"\bi (?:prefer) ([\w '\-]{3,50})", "User prefers {0}."),
            (r"\bi (?:hate|dislike) ([\w '\-]{3,50})", "User dislikes {0}."),
            (r"\bi (?:live|work) (?:in|at) ([\w '\-]{3,50})", "User is at {0}."),
        ]
        facts: list[str] = []
        for pat, tmpl in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                facts.append(tmpl.format(m.group(1).strip().rstrip(".")))
            if len(facts) >= 3:
                break
        return facts

    async def _store_facts(self, user_text: str, user_id: str | None) -> None:
        """Persist extracted facts under namespace 'user:facts' (deduped)."""
        try:
            facts = self._extract_facts(user_text)
            if not facts:
                return
            from app.services.memory.service import MemoryService

            mem = MemoryService(self._db)
            existing = {m.content for m in mem.list(kind="user:facts", limit=200)}
            for fact in facts:
                if fact not in existing:
                    await mem.add(fact, namespace="user:facts", user_id=user_id)
        except Exception as exc:  # noqa: BLE001 - non-blocking
            logger.debug("fact capture skipped: %s", exc)

    # --- summarization hook ---
    async def _maybe_summarize(self, session_id: str) -> None:
        """Best-effort: every SUMMARIZE_EVERY assistant turns, store a summary.

        Swallows all errors so a failed summary never breaks a chat turn.
        """
        try:
            n_assistant = self._db.execute(
                select(func.count())
                .select_from(Message)
                .where(Message.session_id == session_id)
                .where(Message.role == "assistant")
            ).scalar_one()
            if n_assistant and n_assistant % SUMMARIZE_EVERY == 0:
                from app.services.memory.service import MemoryService

                await MemoryService(self._db).summarize_session(session_id)
        except Exception as exc:  # noqa: BLE001 - non-blocking, best-effort
            logger.debug("summarize hook skipped: %s", exc)
