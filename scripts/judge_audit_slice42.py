"""Slice 4.2 hostile judge audit — live API verification."""

from __future__ import annotations

import copy
import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.ids import ontology_uuid
from app.db.session import SessionLocal
from app.main import app
from app.models import Skill, SkillEvidence
from app.ontology.load import AssessmentSpec, load_ontology
from app.services.assessment.loader import AssessmentDriftError, load_assessment_spec

client = TestClient(app)
BUNDLE = load_ontology()
SPECS = {s.slug: s for s in BUNDLE.assessments}
AIML = "ai-ml-engineer"
CYBER = "cybersecurity-analyst"
RESULTS: list[dict] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append({"attack": name, "pass": bool(cond), "detail": detail})
    print(("PASS" if cond else "FAIL"), name, detail[:240])


def learner(tag: str) -> str:
    r = client.post("/v1/learners", json={"display_name": tag})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def evidence(lid: str, skill: str, source: str, level: float, conf: float = 0.85):
    return client.post(
        f"/v1/learners/{lid}/evidence",
        json={"skill": skill, "source": source, "observed_level": level, "confidence": conf},
    )


def make_path(lid: str, role: str = AIML, hours: float = 8, style: str = "MIXED"):
    return client.post(
        f"/v1/learners/{lid}/paths",
        json={"role": role, "weekly_hours": hours, "learning_style": style},
    )


def get_gaps(lid: str, role: str = AIML):
    return client.get(f"/v1/learners/{lid}/roles/{role}/gaps").json()


def submit(lid: str, slug: str, answers: list[int], attempt_id: str | None = None):
    body: dict = {"answers": answers}
    if attempt_id:
        body["attempt_id"] = attempt_id
    return client.post(f"/v1/learners/{lid}/assessments/{slug}/attempts", json=body)


def correct(slug: str) -> list[int]:
    return [q.correct_index for q in SPECS[slug].questions]


def wrong(slug: str) -> list[int]:
    return [(q.correct_index + 1) % len(q.choices) for q in SPECS[slug].questions]


def main() -> None:
    # A1
    lid = learner(f"audit-a1-{uuid.uuid4().hex[:6]}")
    for skill, level in [
        ("python", 0.9),
        ("statistics", 0.35),
        ("ml_fundamentals", 0.55),
        ("supervised_learning", 0.85),
    ]:
        evidence(lid, skill, "ASSESSMENT", level)
    p = make_path(lid).json()
    exe = next(i for i in p["items"] if i["executable"] and i["kind"] == "EXECUTABLE")
    c = exe.get("causality") or {}
    ok(
        "A1",
        bool(c.get("why_selected"))
        and bool(c.get("why_this_skill"))
        and bool(c.get("why_this_resource"))
        and "scored highly" not in c.get("why_selected", "").lower(),
        f"resource={exe['resource']} skill={exe['target_skill']} selected={c.get('why_selected', '')[:100]}",
    )

    # A2
    lid = learner(f"audit-a2-{uuid.uuid4().hex[:6]}")
    evidence(lid, "python", "ASSESSMENT", 0.8)
    evidence(lid, "model_deployment", "ASSESSMENT", 0.3)
    evidence(lid, "supervised_learning", "ASSESSMENT", 0.7)
    p = make_path(lid).json()
    wait = next((i for i in p["items"] if i["kind"] == "WAITING_FOR_VERIFICATION"), None)
    g = get_gaps(lid)
    docker = next((x for x in g["items"] if x["skill"] == "docker"), None)
    ok(
        "A2",
        wait is not None
        and wait["executable"] is False
        and docker is not None
        and docker["evidence_state"] == "UNKNOWN"
        and docker["proficiency"] is None
        and wait.get("eligibility") == "BLOCKED_BY_UNKNOWN",
        f"wait={wait['title'] if wait else None} eligibility={wait.get('eligibility') if wait else None}",
    )

    # A3
    lid = learner(f"audit-a3-{uuid.uuid4().hex[:6]}")
    for skill, level in [
        ("python", 0.9),
        ("statistics", 0.35),
        ("ml_fundamentals", 0.55),
        ("supervised_learning", 0.85),
    ]:
        evidence(lid, skill, "ASSESSMENT", level)
    v1 = make_path(lid).json()
    first = next(i for i in v1["items"] if i["executable"] and i["kind"] == "EXECUTABLE")
    client.post(
        f"/v1/learners/{lid}/paths/{v1['id']}/complete-item",
        json={"position": first["position"]},
    )
    v1_items_before = client.get(f"/v1/learners/{lid}/paths/{v1['id']}").json()["items"]
    r = submit(lid, "model-evaluation-gate", wrong("model-evaluation-gate"))
    v2 = next(
        p for p in client.get(f"/v1/learners/{lid}/paths").json() if p["id"] == r.json()["path_id"]
    )
    v1_after = client.get(f"/v1/learners/{lid}/paths/{v1['id']}").json()
    comp_v1 = next(i for i in v1_items_before if i["position"] == first["position"])
    comp_v2 = next((i for i in v2["items"] if i["resource"] == comp_v1["resource"]), None)
    ok(
        "A3",
        comp_v1["status"] == "COMPLETED"
        and comp_v2 is not None
        and comp_v2["status"] == "COMPLETED"
        and v1_after["status"] == "SUPERSEDED"
        and v1_after["items"] == v1_items_before,
        f"frozen={comp_v1['title']} v2_status={comp_v2['status'] if comp_v2 else None}",
    )

    # A4
    lid = learner(f"audit-a4-{uuid.uuid4().hex[:6]}")
    for skill, level in [
        ("python", 0.9),
        ("statistics", 0.35),
        ("ml_fundamentals", 0.55),
        ("supervised_learning", 0.85),
    ]:
        evidence(lid, skill, "ASSESSMENT", level)
    make_path(lid)
    before = get_gaps(lid)
    me_before = next(x for x in before["items"] if x["skill"] == "model_evaluation")
    r = submit(lid, "model-evaluation-gate", wrong("model-evaluation-gate"))
    body = r.json()
    after = get_gaps(lid)
    me_after = next(x for x in after["items"] if x["skill"] == "model_evaluation")
    ok(
        "A4",
        me_before["evidence_state"] == "UNKNOWN"
        and body.get("skill_results")
        and body.get("diff")
        and me_after["evidence_state"] != "UNKNOWN"
        and body["adaptation"] == "CREATED",
        f"before={me_before['evidence_state']} observed={body['skill_results'][0]['observed_level']} after={me_after['attainment']}",
    )

    # A5
    lid = learner(f"audit-a5-{uuid.uuid4().hex[:6]}")
    make_path(lid)
    g = get_gaps(lid)
    unknowns = [x for x in g["items"] if x["evidence_state"] == "UNKNOWN"]
    ok(
        "A5",
        bool(unknowns) and all(x["proficiency"] is None for x in unknowns),
        f"unknown_count={len(unknowns)} sample_prof={unknowns[0]['proficiency'] if unknowns else 'n/a'}",
    )

    # A6
    lid = learner(f"audit-a6-{uuid.uuid4().hex[:6]}")
    evidence(lid, "python", "ASSESSMENT", 0.8)
    aiml = make_path(lid, role=AIML).json()
    cyber = make_path(lid, role=CYBER).json()
    aiml_skills = {i["target_skill"] for i in aiml["items"]}
    cyber_skills = {i["target_skill"] for i in cyber["items"]}
    ok("A6", aiml_skills != cyber_skills, f"aiml_sample={list(aiml_skills)[:4]} cyber_sample={list(cyber_skills)[:4]}")

    # A7
    l1 = learner(f"audit-a7a-{uuid.uuid4().hex[:6]}")
    l2 = learner(f"audit-a7b-{uuid.uuid4().hex[:6]}")
    evidence(l1, "python", "ASSESSMENT", 0.9)
    evidence(l1, "statistics", "ASSESSMENT", 0.35)
    evidence(l1, "ml_fundamentals", "ASSESSMENT", 0.55)
    evidence(l2, "python", "ASSESSMENT", 0.45)
    evidence(l2, "statistics", "ASSESSMENT", 0.90)
    evidence(l2, "ml_fundamentals", "ASSESSMENT", 0.30)
    p1 = make_path(l1).json()
    p2 = make_path(l2).json()
    ok("A7", p1["items"] != p2["items"], "paths differ by evidence profile")

    # A8
    lid = learner(f"audit-a8-{uuid.uuid4().hex[:6]}")
    for skill, level in [
        ("python", 0.9),
        ("statistics", 0.35),
        ("ml_fundamentals", 0.55),
        ("supervised_learning", 0.85),
    ]:
        evidence(lid, skill, "ASSESSMENT", level)
    p5 = make_path(lid, hours=5).json()
    p15 = make_path(lid, hours=15).json()
    ok(
        "A8",
        p5["weekly_hours"] != p15["weekly_hours"]
        or p5["total_estimated_hours"] != p15["total_estimated_hours"]
        or [
            i["resource"]
            for i in p5["items"]
            if i["kind"] == "EXECUTABLE"
        ]
        != [
            i["resource"]
            for i in p15["items"]
            if i["kind"] == "EXECUTABLE"
        ],
        f"5h_total={p5['total_estimated_hours']} 15h_total={p15['total_estimated_hours']}",
    )

    # A9
    lid = learner(f"audit-a9-{uuid.uuid4().hex[:6]}")
    for skill, level in [
        ("python", 0.9),
        ("statistics", 0.35),
        ("ml_fundamentals", 0.55),
        ("supervised_learning", 0.85),
    ]:
        evidence(lid, skill, "ASSESSMENT", level)
    pr = make_path(lid, style="READING").json()
    pv = make_path(lid, style="VIDEO").json()
    ph = make_path(lid, style="HANDS_ON").json()
    ok(
        "A9",
        pr["learning_style"] == "READING"
        and pv["learning_style"] == "VIDEO"
        and ph["learning_style"] == "HANDS_ON",
        "learning_style persisted per path request",
    )

    # A10
    lid = learner(f"audit-a10-{uuid.uuid4().hex[:6]}")
    evidence(lid, "python", "SELF_REPORT", 0.90)
    make_path(lid)
    submit(lid, "python-gate", [1, 0, 0])
    skills = client.get(f"/v1/learners/{lid}/skills").json()
    py = next(s for s in skills if s["skill"] == "python")
    session = SessionLocal()
    try:
        rows = session.scalars(
            select(SkillEvidence)
            .join(Skill, Skill.id == SkillEvidence.skill_id)
            .where(SkillEvidence.user_id == uuid.UUID(lid), Skill.slug == "python")
        ).all()
    finally:
        session.close()
    ok(
        "A10",
        py["conflict"]
        and len(rows) == 2
        and {r.source_type for r in rows} == {"SELF_REPORT", "ASSESSMENT"}
        and 0.50 < py["proficiency"] < 0.90,
        f"prof={py['proficiency']} conflict={py['conflict']}",
    )

    # A11
    lid = learner(f"audit-a11-{uuid.uuid4().hex[:6]}")
    make_path(lid)
    aid = str(uuid.uuid4())
    first = submit(lid, "statistics-gate", correct("statistics-gate"), aid)
    second = submit(lid, "statistics-gate", correct("statistics-gate"), aid)
    paths_ct = len(client.get(f"/v1/learners/{lid}/paths").json())
    ok(
        "A11",
        second.json()["adaptation"] == "REPLAYED" and paths_ct == 1,
        f"adaptation={second.json()['adaptation']} paths={paths_ct}",
    )

    # A12
    lid = learner(f"audit-a12-{uuid.uuid4().hex[:6]}")
    for skill, level in [
        ("python", 0.92),
        ("statistics", 0.40),
        ("ml_fundamentals", 0.55),
        ("model_evaluation", 0.88),
    ]:
        evidence(lid, skill, "ASSESSMENT", level)
    make_path(lid)
    r = submit(lid, "model-evaluation-gate", correct("model-evaluation-gate"))
    ok(
        "A12",
        r.json()["adaptation"] == "NO_ADAPTATION_REQUIRED"
        and len(client.get(f"/v1/learners/{lid}/paths").json()) == 1,
        f"adaptation={r.json()['adaptation']}",
    )

    # A13
    session = SessionLocal()
    try:
        assessment_id = ontology_uuid("assessment", "python-gate")
        yaml_spec = next(spec for spec in BUNDLE.assessments if spec.slug == "python-gate")
        drifted = AssessmentSpec(
            slug=yaml_spec.slug,
            title=yaml_spec.title,
            description=yaml_spec.description,
            primary_skill=yaml_spec.primary_skill,
            pass_threshold=0.41,
            questions=yaml_spec.questions,
            target_role=yaml_spec.target_role,
            target_skills=yaml_spec.target_skills,
        )
        try:
            load_assessment_spec(session, assessment_id=assessment_id, yaml_spec=drifted)
            drift_ok = False
        except AssessmentDriftError as exc:
            drift_ok = exc.code == "DRIFT_DETECTED"
    finally:
        session.close()
    ok("A13", drift_ok, "DRIFT_DETECTED raised on hash mismatch")

    # A14
    lid = learner(f"audit-a14-{uuid.uuid4().hex[:6]}")
    for skill, level in [
        ("python", 0.9),
        ("statistics", 0.35),
        ("ml_fundamentals", 0.55),
        ("supervised_learning", 0.85),
    ]:
        evidence(lid, skill, "ASSESSMENT", level)
    v1 = make_path(lid).json()
    submit(lid, "model-evaluation-gate", wrong("model-evaluation-gate"))
    submit(lid, "statistics-gate", correct("statistics-gate"))
    paths = client.get(f"/v1/learners/{lid}/paths").json()
    timeline = client.get(f"/v1/learners/{lid}/roles/{AIML}/path-timeline").json()
    active = [p for p in paths if p["status"] == "ACTIVE"]
    versions = sorted(paths, key=lambda row: row["version"])
    ok(
        "A14",
        len(paths) == 3
        and len(active) == 1
        and [t["version"] for t in timeline] == [1, 2, 3]
        and versions[0]["status"] == "SUPERSEDED"
        and versions[1]["status"] == "SUPERSEDED"
        and versions[2]["status"] == "ACTIVE",
        f"versions={[p['version'] for p in versions]} active={active[0]['version']}",
    )

    passed = sum(1 for row in RESULTS if row["pass"])
    print("SUMMARY", passed, "/", len(RESULTS))
    print(json.dumps(RESULTS, indent=2))


if __name__ == "__main__":
    main()
