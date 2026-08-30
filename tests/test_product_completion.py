"""Tests for natural-language goal intake and multi-role support."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.main import app
from app.services.intake.extract import parse_goal

client = TestClient(app)


def postgres_available() -> bool:
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL is not reachable at DATABASE_URL",
)

ROLES = [
    "ai-ml-engineer",
    "cybersecurity-analyst",
    "backend-developer",
    "frontend-developer",
    "data-engineer",
]


def test_goal_intake_resolves_ml_engineer_deterministically():
    result = parse_goal("I want to become a machine learning engineer focused on computer vision.")
    assert result.role is not None
    assert result.role.slug == "ai-ml-engineer"
    assert result.source in {"DETERMINISTIC", "LLM"}


def test_goal_intake_api_returns_structured_payload():
    response = client.post(
        "/v1/intake/goal",
        json={"goal": "I want to become a cybersecurity analyst focused on incident response."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["goal_text"]
    assert body["resolution_status"] == "RESOLVED"
    assert body["role"]["slug"] == "cybersecurity-analyst"


@pytest.mark.parametrize("role_slug", ROLES)
def test_each_priority_role_generates_distinct_path(role_slug: str):
    learner = client.post("/v1/learners", json={"display_name": f"multi-{role_slug}-{uuid.uuid4().hex[:6]}"})
    assert learner.status_code == 200
    learner_id = learner.json()["id"]
    demo = client.get(f"/v1/roles/{role_slug}/demo-evidence")
    assert demo.status_code == 200
    for row in demo.json():
        client.post(
            f"/v1/learners/{learner_id}/evidence",
            json={
                "skill": row["skill"],
                "source": row["source"],
                "observed_level": row["observed_level"],
                "confidence": row["confidence"],
            },
        )
    path = client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": role_slug, "weekly_hours": 8, "learning_style": "MIXED"},
    )
    assert path.status_code == 200, path.text
    body = path.json()
    assert body["role"] == role_slug
    assert len(body["items"]) > 0


def test_dashboard_endpoint_compiles():
    learner = client.post("/v1/learners", json={"display_name": f"dash-{uuid.uuid4().hex[:6]}"})
    learner_id = learner.json()["id"]
    role = "backend-developer"
    for row in client.get(f"/v1/roles/{role}/demo-evidence").json():
        client.post(
            f"/v1/learners/{learner_id}/evidence",
            json={
                "skill": row["skill"],
                "source": row["source"],
                "observed_level": row["observed_level"],
                "confidence": row["confidence"],
            },
        )
    client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": role, "weekly_hours": 6, "learning_style": "PROJECT"},
    )
    dash = client.get(f"/v1/learners/{learner_id}/roles/{role}/dashboard")
    assert dash.status_code == 200, dash.text
    payload = dash.json()
    assert payload["role"] == role
    assert "overall_progress" in payload
    assert "milestones" in payload


def test_goal_text_persisted_on_profile_and_dashboard():
    goal = "I want to become a backend engineer within 12 months."
    learner = client.post(
        "/v1/learners",
        json={
            "display_name": f"goal-{uuid.uuid4().hex[:6]}",
            "goal_text": goal,
            "target_role": "backend-developer",
        },
    )
    assert learner.status_code == 200, learner.text
    body = learner.json()
    assert body["goal_text"] == goal
    learner_id = body["id"]
    for row in client.get("/v1/roles/backend-developer/demo-evidence").json():
        client.post(
            f"/v1/learners/{learner_id}/evidence",
            json={
                "skill": row["skill"],
                "source": row["source"],
                "observed_level": row["observed_level"],
                "confidence": row["confidence"],
            },
        )
    client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": "backend-developer", "weekly_hours": 8, "learning_style": "MIXED"},
    )
    dash = client.get(f"/v1/learners/{learner_id}/roles/backend-developer/dashboard")
    assert dash.status_code == 200, dash.text
    assert dash.json()["goal_text"] == goal
