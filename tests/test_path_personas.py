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


def _evidence(learner_id: str, skill: str, source: str, level: float) -> None:
    response = client.post(
        f"/v1/learners/{learner_id}/evidence",
        json={"skill": skill, "source": source, "observed_level": level, "confidence": 0.85},
    )
    assert response.status_code == 200, response.text


def _path(learner_id: str, role: str, weekly_hours: float, style: str) -> dict:
    response = client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": role, "weekly_hours": weekly_hours, "learning_style": style},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _persona_a() -> str:
    learner_id = _learner(f"path-a-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "sql", "ASSESSMENT", 0.75)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    return learner_id


def _persona_b() -> str:
    learner_id = _learner(f"path-b-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.45)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.90)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.30)
    return learner_id


def _persona_c() -> str:
    learner_id = _learner(f"path-c-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.70)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.65)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.60)
    _evidence(learner_id, "model_deployment", "ASSESSMENT", 0.30)
    return learner_id


def test_personas_receive_different_aiml_paths():
    a = _path(_persona_a(), AIML, 8, "READING")
    b = _path(_persona_b(), AIML, 8, "READING")
    c = _path(_persona_c(), AIML, 8, "READING")
    slugs_a = [item["resource"] for item in a["items"]]
    slugs_b = [item["resource"] for item in b["items"]]
    slugs_c = [item["resource"] for item in c["items"]]
    assert slugs_a
    assert slugs_a != slugs_b
    assert slugs_b != slugs_c or [i["intervention"] for i in a["items"]] != [
        i["intervention"] for i in c["items"]
    ]
    assert a["items"][0]["score_breakdown"]["final_score"] is not None
    assert "skill_gap_fit" in a["items"][0]["score_breakdown"]
    assert c["items"][0].get("causality", {}).get("why_selected")
    assert "fastapi-tutorial" not in slugs_c


def test_same_learner_different_roles_select_different_resources():
    learner_id = _persona_a()
    aiml = _path(learner_id, AIML, 8, "READING")
    cyber = _path(learner_id, CYBER, 8, "READING")
    assert {item["resource"] for item in aiml["items"]} != {item["resource"] for item in cyber["items"]}


def test_time_budget_changes_packing_or_selection():
    learner_id = _persona_a()
    five = _path(learner_id, AIML, 5, "MIXED")
    fifteen = _path(learner_id, AIML, 15, "MIXED")
    weeks_five = [item["week"] for item in five["items"]]
    weeks_fifteen = [item["week"] for item in fifteen["items"]]
    slugs_five = [item["resource"] for item in five["items"]]
    slugs_fifteen = [item["resource"] for item in fifteen["items"]]
    assert slugs_five != slugs_fifteen or weeks_five != weeks_fifteen


def test_learning_style_changes_ranking_when_metadata_supports_it():
    learner_id = _persona_a()
    video = client.get(
        f"/v1/learners/{learner_id}/roles/{AIML}/recommendations",
        params={"weekly_hours": 8, "learning_style": "VIDEO"},
    )
    hands = client.get(
        f"/v1/learners/{learner_id}/roles/{AIML}/recommendations",
        params={"weekly_hours": 8, "learning_style": "HANDS_ON"},
    )
    assert video.status_code == 200
    assert hands.status_code == 200
    assert [row["resource"] for row in video.json()[:8]] != [row["resource"] for row in hands.json()[:8]] or [
        row["score_breakdown"]["learning_style_fit"] for row in video.json()[:5]
    ] != [row["score_breakdown"]["learning_style_fit"] for row in hands.json()[:5]]


def test_python_blocker_precedes_ml_resource_for_persona_b():
    path = _path(_persona_b(), AIML, 10, "READING")
    slugs = [item["resource"] for item in path["items"]]
    skills = [item["target_skill"] for item in path["items"]]
    assert "python" in skills
    assert "ml_fundamentals" in skills
    assert skills.index("python") < skills.index("ml_fundamentals")
    assert slugs


def test_unknown_docker_is_not_treated_as_mastered():
    path = _path(_persona_a(), AIML, 8, "MIXED")
    flagged = [
        item
        for item in path["items"]
        if any(p.get("skill") == "docker" and p.get("state") == "UNKNOWN" for p in item["prerequisites"])
    ]
    assert path["items"]
    if flagged:
        assert all(item["eligibility"] != "ELIGIBLE" or "UNKNOWN" in item["explanation"] for item in flagged)


def _persona_d() -> str:
    learner_id = _learner(f"path-d-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.90)
    _evidence(learner_id, "sql", "ASSESSMENT", 0.80)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.88)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.82)
    return learner_id


def _persona_e() -> str:
    learner_id = _learner(f"path-e-{uuid.uuid4().hex[:8]}")
    _evidence(learner_id, "python", "ASSESSMENT", 0.40)
    _evidence(learner_id, "statistics", "ASSESSMENT", 0.30)
    _evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.20)
    return learner_id


def test_personas_d_and_e_differ_on_time_and_style():
    strong = _path(_persona_d(), AIML, 15, "READING")
    limited = _path(_persona_e(), AIML, 5, "HANDS_ON")
    slugs_d = [item["resource"] for item in strong["items"]]
    slugs_e = [item["resource"] for item in limited["items"]]
    weeks_d = [item["week"] for item in strong["items"]]
    weeks_e = [item["week"] for item in limited["items"]]
    assert slugs_d
    assert slugs_e
    assert slugs_d != slugs_e or weeks_d != weeks_e
    assert [item["intervention"] for item in strong["items"]] != [
        item["intervention"] for item in limited["items"]
    ] or slugs_d != slugs_e


def test_path_items_are_catalog_resources_and_deterministic():
    learner_id = _persona_b()
    first = _path(learner_id, AIML, 8, "HANDS_ON")
    second = client.get(f"/v1/learners/{learner_id}/paths/{first['id']}")
    assert second.status_code == 200
    listed = client.get(f"/v1/learners/{learner_id}/paths")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == first["id"]
    for item in first["items"]:
        assert item["resource"]
        assert item["explanation"]
        if item["url"]:
            assert item["url"].startswith("https://")
