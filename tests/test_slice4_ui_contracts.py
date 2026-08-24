"""Slice 4.0 UI contract tests — presentation endpoints only.

Does not change scoring, fusion, gaps, or adaptation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.main import app

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


requires_db = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL is not reachable at DATABASE_URL",
)


@requires_db
def test_list_roles_includes_aiml():
    response = client.get("/v1/roles")
    assert response.status_code == 200, response.text
    slugs = {item["slug"] for item in response.json()}
    assert "ai-ml-engineer" in slugs


@requires_db
def test_list_evidence_for_skill_returns_rows():
    learner = client.post("/v1/learners", json={"display_name": "slice43-evidence"}).json()
    learner_id = learner["id"]
    client.post(
        f"/v1/learners/{learner_id}/evidence",
        json={
            "skill": "python",
            "source": "SELF_REPORT",
            "observed_level": 0.9,
            "confidence": 0.8,
        },
    )
    response = client.get(f"/v1/learners/{learner_id}/evidence", params={"skill": "python"})
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["skill"] == "python"
    assert rows[0]["source"] == "SELF_REPORT"
    assert rows[0]["observed_level"] == 0.9
    assert "reliability" in rows[0]


@requires_db
def test_assessment_public_copy_omits_answers():
    response = client.get("/v1/assessments/model-evaluation-gate")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["slug"] == "model-evaluation-gate"
    assert body["question_count"] == len(body["questions"])
    assert body["question_count"] >= 1
    dumped = response.text
    assert "correct_index" not in dumped
    assert "correctIndex" not in dumped
    for question in body["questions"]:
        assert "prompt" in question
        assert "choices" in question
        assert "correct_index" not in question
        assert "explanation" not in question
