"""Plan CRUD + step action endpoint tests against in-memory SQLite.

Covers: plan create/list/get/cancel, step approve/retry, sub-plan creation,
auth enforcement (401 without token) and WebSocket status broadcasting (the
plans router's ``manager`` is replaced with a recording double).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.routers.plans as plans_router
from app.core.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.routers.plans import router as plan_router

TEST_USER = "test-user"


class _RecordingManager:
    """Async broadcast double that records every ("channel", payload) call."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def broadcast(self, channel: str, payload: dict) -> None:
        self.events.append((channel, payload))


@pytest.fixture()
def broadcasts(monkeypatch) -> _RecordingManager:
    rec = _RecordingManager()
    monkeypatch.setattr(plans_router, "manager", rec)
    return rec


@pytest.fixture()
def client(db, broadcasts) -> TestClient:
    """App exposing only the plans router with db + auth overridden."""
    app = FastAPI()
    app.include_router(plan_router, prefix="/api")

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    return TestClient(app)


def _create_plan(client: TestClient, **kwargs) -> dict:
    body = {
        "goal": "Do the thing",
        "trust_level": "manual",
        "parallel": False,
    }
    body.update(kwargs)
    res = client.post("/api/plans", json=body)
    assert res.status_code == 200, res.text
    return res.json()


# --- Plan CRUD ---


def test_create_plan(client, broadcasts):
    plan = _create_plan(client, goal="Book a flight", parallel=True)
    assert plan["goal"] == "Book a flight"
    assert plan["user_id"] == TEST_USER
    assert plan["parallel"] is True
    assert plan["status"] == "pending"
    assert plan["trust_level"] == "manual"
    # Broadcasting a plan_created event.
    assert any(p.get("type") == "plan_created" for _, p in broadcasts.events)


def test_create_plan_with_steps(client):
    res = client.post(
        "/api/plans",
        json={
            "goal": "Multi-step",
            "steps": [
                {"action": "open_browser", "args_json": {"url": "x"}, "step_order": 0},
                {"action": "click", "args_json": "{}", "step_order": 1},
            ],
        },
    )
    assert res.status_code == 200, res.text
    plan_id = res.json()["id"]

    detail = client.get(f"/api/plans/{plan_id}").json()
    assert len(detail["steps"]) == 2
    assert detail["steps"][0]["action"] == "open_browser"


def test_list_plans(client):
    _create_plan(client, goal="one")
    _create_plan(client, goal="two")
    res = client.get("/api/plans")
    assert res.status_code == 200
    goals = {p["goal"] for p in res.json()}
    assert {"one", "two"} <= goals


def test_get_plan(client):
    plan = _create_plan(client)
    res = client.get(f"/api/plans/{plan['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == plan["id"]
    assert body["steps"] == []


def test_get_plan_not_found(client):
    res = client.get("/api/plans/does-not-exist")
    assert res.status_code == 404


def test_cancel_plan(client, broadcasts):
    plan = _create_plan(client)
    res = client.post(f"/api/plans/{plan['id']}/cancel")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "cancelled"
    assert body["completed_at"] is not None
    assert any(p.get("type") == "plan_cancelled" for _, p in broadcasts.events)


# --- Step actions ---


def test_approve_step(client, broadcasts):
    res = client.post(
        "/api/plans",
        json={
            "goal": "approve me",
            "steps": [{"action": "run", "step_order": 0}],
        },
    )
    plan = res.json()
    step_id = client.get(f"/api/plans/{plan['id']}").json()["steps"][0]["id"]

    # Put the step into pending_approval via the DB-backed retry helper
    # (non-god plan), then approve it.
    client.post(f"/api/plans/{plan['id']}/steps/{step_id}/retry")

    res = client.post(f"/api/plans/{plan['id']}/steps/{step_id}/approve")
    assert res.status_code == 200
    assert res.json()["detail"] == "approved"
    assert any(p.get("type") == "step_started" for _, p in broadcasts.events)


def test_approve_step_not_pending(client):
    res = client.post(
        "/api/plans",
        json={"goal": "g", "steps": [{"action": "run", "step_order": 0}]},
    )
    plan = res.json()
    step_id = client.get(f"/api/plans/{plan['id']}").json()["steps"][0]["id"]
    # Default status is "pending", not "pending_approval".
    res = client.post(f"/api/plans/{plan['id']}/steps/{step_id}/approve")
    assert res.status_code == 400


def test_retry_step(client, broadcasts):
    res = client.post(
        "/api/plans",
        json={"goal": "g", "steps": [{"action": "run", "step_order": 0}]},
    )
    plan = res.json()
    step_id = client.get(f"/api/plans/{plan['id']}").json()["steps"][0]["id"]

    res = client.post(f"/api/plans/{plan['id']}/steps/{step_id}/retry")
    assert res.status_code == 200
    body = res.json()
    assert body["retries"] == 1
    # Non-god trust level requires re-approval.
    assert body["status"] == "pending_approval"
    assert any(p.get("type") == "step_approval_needed" for _, p in broadcasts.events)


def test_retry_step_god_runs_immediately(client):
    res = client.post(
        "/api/plans",
        json={
            "goal": "g",
            "trust_level": "god",
            "steps": [{"action": "run", "step_order": 0}],
        },
    )
    plan = res.json()
    step_id = client.get(f"/api/plans/{plan['id']}").json()["steps"][0]["id"]
    res = client.post(f"/api/plans/{plan['id']}/steps/{step_id}/retry")
    assert res.json()["status"] == "running"


def test_retry_step_not_found(client):
    plan = _create_plan(client)
    res = client.post(f"/api/plans/{plan['id']}/steps/missing/retry")
    assert res.status_code == 404


# --- Sub-plans ---


def test_create_subplan(client, broadcasts):
    res = client.post(
        "/api/plans",
        json={"goal": "parent", "steps": [{"action": "delegate", "step_order": 0}]},
    )
    plan = res.json()
    parent_step_id = client.get(f"/api/plans/{plan['id']}").json()["steps"][0]["id"]

    res = client.post(
        f"/api/plans/{plan['id']}/subplans",
        json={"parent_step_id": parent_step_id, "goal": "child goal"},
    )
    assert res.status_code == 200, res.text
    sub = res.json()
    assert sub["goal"] == "child goal"
    assert sub["id"] != plan["id"]
    assert any(p.get("type") == "subplan_created" for _, p in broadcasts.events)


def test_create_subplan_bad_parent(client):
    plan = _create_plan(client)
    res = client.post(
        f"/api/plans/{plan['id']}/subplans",
        json={"parent_step_id": "nope", "goal": "child"},
    )
    assert res.status_code == 404


# --- Auth enforcement ---


def test_auth_required_without_token(db, broadcasts, monkeypatch):
    """With MIORI_API_TOKEN set, calls without a Bearer token get 401."""
    monkeypatch.setattr(settings, "MIORI_API_TOKEN", "secret-token")

    app = FastAPI()
    app.include_router(plan_router, prefix="/api")

    def _override_db():
        yield db

    # Only override the db, NOT get_current_user, so real auth runs.
    app.dependency_overrides[get_db] = _override_db
    unauth = TestClient(app)

    res = unauth.get("/api/plans")
    assert res.status_code == 401

    # A wrong token is likewise rejected before any DB access.
    res = unauth.get("/api/plans", headers={"Authorization": "Bearer wrong"})
    assert res.status_code == 401
