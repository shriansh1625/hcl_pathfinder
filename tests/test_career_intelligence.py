from __future__ import annotations

import uuid

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


pytestmark = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL is not reachable at DATABASE_URL",
)

AIML = "ai-ml-engineer"
CYBER = "cybersecurity-analyst"


def _learner(name: str) -> str:
    response = client.post("/v1/learners", json={"display_name": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _evidence(learner_id: str, skill: str, source: str, level: float, confidence: float = 0.85) -> None:
    response = client.post(
        f"/v1/learners/{learner_id}/evidence",
        json={
            "skill": skill,
            "source": source,
            "observed_level": level,
            "confidence": confidence,
        },
    )
    assert response.status_code == 200, response.text


def _gaps(learner_id: str, role: str) -> dict:
    response = client.get(f"/v1/learners/{learner_id}/roles/{role}/gaps")
    assert response.status_code == 200, response.text
    return response.json()


def _by_skill(profile: dict) -> dict[str, dict]:
    return {item["skill"]: item for item in profile["items"]}


def _persona_a() -> str:
    learner_id = _learner(f"persona-a-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "sql", "ASSESSMENT", 0.75)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    return learner_id


def _persona_b() -> str:
    learner_id = _learner(f"persona-b-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.45)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.90)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.30)
    return learner_id


def _persona_c() -> str:
    learner_id = _learner(f"persona-c-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.70)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.65)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.60)
    _evidence(learner_id, "model_deployment", "ASSESSMENT", 0.30)
    return learner_id


def test_role_competencies_endpoint():
    response = client.get(f"/v1/roles/{AIML}/competencies")
    assert response.status_code == 200
    body = response.json()
    slugs = {item["skill"] for item in body["competencies"]}
    assert "python" in slugs
    assert "model_deployment" in slugs
    assert "owasp_top10" not in slugs


def test_three_personas_have_different_aiml_gap_profiles():
    a = _by_skill(_gaps(_persona_a(), AIML))
    b = _by_skill(_gaps(_persona_b(), AIML))
    c = _by_skill(_gaps(_persona_c(), AIML))

    assert a["python"]["gap_status"] == "SATISFIED"
    assert a["statistics"]["gap_status"] == "GAP"
    assert a["model_deployment"]["gap_status"] == "UNKNOWN"

    assert b["python"]["gap_status"] == "GAP"
    assert b["statistics"]["gap_status"] == "SATISFIED"
    assert b["ml_fundamentals"]["gap"] > a["ml_fundamentals"]["gap"]

    assert c["model_deployment"]["gap_status"] == "GAP"
    assert c["model_deployment"]["proficiency"] == pytest.approx(0.30)

    assert a["statistics"]["priority"] != b["statistics"]["priority"]
    assert a["python"]["priority"] != b["python"]["priority"]


def test_same_learner_different_roles_change_gaps():
    learner_id = _persona_a()
    aiml = _by_skill(_gaps(learner_id, AIML))
    cyber = _by_skill(_gaps(learner_id, CYBER))
    assert "statistics" in aiml
    assert "statistics" not in cyber
    assert "owasp_top10" in cyber
    assert "owasp_top10" not in aiml
    assert cyber["owasp_top10"]["gap_status"] == "UNKNOWN"
    assert aiml["python"]["target_level"] != cyber["python"]["target_level"]


def test_unknown_mlops_is_not_zero():
    learner_id = _persona_a()
    item = _by_skill(_gaps(learner_id, AIML))["model_deployment"]
    assert item["gap_status"] == "UNKNOWN"
    assert item["proficiency"] is None
    assert item["gap"] is None
    assert "UNKNOWN" in item["explanation"]
    assert "beginner" not in item["explanation"].lower() or "not a beginner" in item["explanation"].lower()


def test_evidence_conflict_is_inspectable_and_append_only():
    learner_id = _learner(f"conflict-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "SELF_REPORT", 0.90, 0.80)
    _evidence(learner_id, "python", "ASSESSMENT", 0.55, 0.80)
    skills = client.get(f"/v1/learners/{learner_id}/skills").json()
    python = next(item for item in skills if item["skill"] == "python")
    assert python["conflict"] is True
    assert python["dominant_source"] == "ASSESSMENT"
    assert python["evidence_count"] == 2
    assert python["proficiency"] is not None
    assert 0.55 < python["proficiency"] < 0.90


def test_gap_explanations_are_grounded():
    profile = _gaps(_persona_a(), AIML)
    stats = _by_skill(profile)["statistics"]
    assert "Statistics" in stats["explanation"] or "statistics" in stats["explanation"].lower()
    assert "75%" in stats["explanation"] or "80%" in stats["explanation"]
    assert stats["hard_downstream"] or stats["soft_downstream"] or stats["priority"] >= 0


def test_python_blocking_impact_is_visible_on_aiml():
    item = _by_skill(_gaps(_persona_b(), AIML))["python"]
    assert item["is_blocking"] is True
    assert "ml_fundamentals" in item["hard_downstream"]
    assert item["prerequisite_criticality"] > 1.0
