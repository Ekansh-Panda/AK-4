"""Offline mock model provider.

Echoes the last user message back with a friendly Miori-flavored wrapper and
streams it token-by-token so the WebSocket chat path works without any real
model or network access.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable

from app.services.providers.base import ChatMessage, ModelDescriptor, ModelProvider


class MockProvider(ModelProvider):
    name = "mock"

    def list_models(self) -> list[ModelDescriptor]:
        return [
            ModelDescriptor(
                id="mock-echo",
                name="Miori Mock Echo",
                provider=self.name,
                context_window=8192,
            )
        ]

    def _compose_reply(self, messages: Iterable[ChatMessage]) -> str:
        last_user = ""
        for m in messages:
            if m.role == "user" and m.content:
                last_user = m.content
        if not last_user:
            return "Hey, I'm here. What's on your mind?"
        return f"(mock) I heard you say: {last_user}"

    async def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> str | ChatMessage:
        msgs = list(messages)
        reply = self._compose_reply(msgs)
        if tools and "task" in reply.lower() and msgs and msgs[-1].role == "user":
            # mock tool call
            return ChatMessage(
                role="assistant",
                content=None,
                tool_calls=[{
                    "id": "mock_call_1",
                    "type": "function",
                    "function": {
                        "name": "manage_tasks",
                        "arguments": '{"action": "list"}'
                    }
                }]
            )
        return reply

    async def stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str | ChatMessage]:
        msgs = list(messages)
        reply = self._compose_reply(msgs)
        if tools and "task" in reply.lower() and msgs and msgs[-1].role == "user":
            yield ChatMessage(
                role="assistant",
                content=None,
                tool_calls=[{
                    "id": "mock_call_1",
                    "type": "function",
                    "function": {
                        "name": "manage_tasks",
                        "arguments": '{"action": "list"}'
                    }
                }]
            )
            return
            
        for token in reply.split(" "):
            await asyncio.sleep(0.02)  # simulate generation latency
            yield token + " "
