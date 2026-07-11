"""Tests for the LiteLLM orchestrator provider."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.providers.base import ChatMessage
from app.services.providers.capability_matrix import list_models, get_capability
from app.services.providers.mock_provider import MockProvider
from app.services.providers.orchestrator import (
    OrchestratingProvider,
    RouterBuildError,
    _build_litellm_deployments,
)


def test_capability_matrix_lists_models():
    models = list_models("openai")
    ids = {m.id for m in models}
    assert "gpt-4o-mini" in ids


def test_get_capability_missing():
    assert get_capability("openai", "does-not-exist") is None


def test_build_deployments_returns_empty_without_keys():
    assert _build_litellm_deployments({}) == []


def _mock_response(content: str = "hi"):
    mock = MagicMock()
    choice = MagicMock()
    message = MagicMock()
    message.content = content
    message.tool_calls = None
    choice.message = message
    choice.choices = [choice]
    mock.choices = [choice]
    return mock


def _mock_stream_chunk(content: str):
    chunk = MagicMock()
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = None
    chunk.choices = [MagicMock(delta=delta)]
    return chunk


def test_chat_success_sets_last_served():
    orch = OrchestratingProvider()
    mock_router = AsyncMock()
    mock_router.acompletion = AsyncMock(return_value=_mock_response("ok"))
    orch._router_factory = lambda: mock_router
    orch._router = None
    orch.available = lambda: True
    result = asyncio.run(orch.chat([ChatMessage(role="user", content="hi")]))
    assert result == "ok"
    assert orch.last_served() is not None


def test_stream_success_yields_tokens():
    async def _gen():
        for token in ["hel", "lo"]:
            yield _mock_stream_chunk(token)

    orch = OrchestratingProvider()
    mock_router = AsyncMock()
    mock_router.acompletion = AsyncMock(return_value=_gen())
    mock_router.astream = AsyncMock(return_value=_gen())
    orch._router_factory = lambda: mock_router
    orch._router = None
    orch.available = lambda: True

    async def _run():
        tokens = []
        async for chunk in orch.stream([ChatMessage(role="user", content="hi")]):
            tokens.append(chunk)
        return tokens

    tokens = asyncio.run(_run())
    assert tokens == ["hel", "lo"]


def test_pool_exhausted_falls_back_to_mock():
    orch = OrchestratingProvider()
    mock_router = AsyncMock()
    mock_router.acompletion = AsyncMock(side_effect=Exception("429"))
    orch._router_factory = lambda: mock_router
    orch._router = None
    orch.available = lambda: True
    result = asyncio.run(orch.chat([ChatMessage(role="user", content="hi")]))
    assert "(mock)" in result
    assert orch.last_served() == ("mock", "mock-echo")


def test_non_retryable_short_circuits():
    orch = OrchestratingProvider()
    mock_router = AsyncMock()
    mock_router.acompletion = AsyncMock(side_effect=Exception("401"))
    orch._router_factory = lambda: mock_router
    orch._router = None
    orch.available = lambda: True
    result = asyncio.run(orch.chat([ChatMessage(role="user", content="hi")]))
    assert "(mock)" in result


def test_router_build_error_falls_back_to_mock():
    orch = OrchestratingProvider()
    orch._router_factory = None
    with patch.object(orch, "_resolve_keys", return_value={}):
        result = asyncio.run(orch.chat([ChatMessage(role="user", content="hi")]))
        assert "(mock)" in result
        assert orch.last_served() == ("mock", "mock-echo")
