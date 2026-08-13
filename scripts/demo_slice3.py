"""Slice 3 demo scenarios A-E with execution evidence.

Runs through the real domain logic: API -> assessment runtime -> evidence ->
fusion -> gap profile -> adaptation -> Path V2 -> diff. No demo-only code.

Usage: python scripts/demo_slice3.py
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.ontology.load import load_ontology

client = TestClient(app)
BUNDLE = load_ontology()
SPECS = {item.slug: item for item in BUNDLE.assessments}
AIML = "ai-ml-engineer"


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def learner(name: str) -> str:
    return client.post("/v1/learners", json={"display_name": name}).json()["id"]


def evidence(learner_id: str, skill: str, source: str, level: float, confidence: float = 0.85):
    client.post(
        f"/v1/learners/{learner_id}/evidence",
        json={
            "skill": skill,
            "source": source,
            "observed_level": level,
            "confidence": confidence,
        },
    ).raise_for_status()


def make_path(learner_id: str, role: str = AIML, hours: float = 10) -> dict:
    response = client.post(
        f"/v1/learners/{learner_id}/paths",
        json={"role": role, "weekly_hours": hours, "learning_style": "MIXED"},
    )
    response.raise_for_status()
    return response.json()


def submit(learner_id: str, slug: str, answers: list[int]) -> dict:
    response = client.post(
        f"/v1/learners/{learner_id}/assessments/{slug}/attempts", json={"answers": answers}
    )
    response.raise_for_status()
    return response.json()


def correct(slug: str) -> list[int]:
    return [q.correct_index for q in SPECS[slug].questions]


def wrong(slug: str) -> list[int]:
    return [(q.correct_index + 1) % len(q.choices) for q in SPECS[slug].questions]


def show_path(path: dict, label: str) -> None:
    print(f"{label}  (version={path['version']} status={path['status']} hours={path['total_estimated_hours']})")
    for item in path["items"]:
        gate = f" gate={item['gate']['skill']}" if item.get("gate") else ""
        print(
            f"  pos{item['position']:<3d} w{str(item['week']):<4s} {item['kind']:<26s} "
            f"exec={str(item['executable']):<5s} {item['resource'] or item['title']}{gate}"
        )


def show_diff(diff: dict) -> None:
    print(f"changed_skills: {diff['changed_skills']}")
    for section in ("added", "removed", "moved", "blocked"):
        entries = diff[section]
        if not entries:
            continue
        print(f"{section.upper()}:")
        for entry in entries:
            weeks = ""
            if entry.get("from_week") is not None or entry.get("to_week") is not None:
                weeks = f" (week {entry.get('from_week')} -> {entry.get('to_week')})"
            print(f"  - {entry['key']}{weeks}")
            print(f"      {entry['reason']}")


def scenario_primary() -> None:
    banner("SCENARIO A (primary): UNKNOWN -> assessment fails -> GAP -> PATH V2")
    uid = learner(f"demo-a-{uuid.uuid4().hex[:6]}")
    evidence(uid, "python", "ASSESSMENT", 0.90)
    evidence(uid, "statistics", "ASSESSMENT", 0.35)
    evidence(uid, "ml_fundamentals", "ASSESSMENT", 0.55)
    evidence(uid, "supervised_learning", "ASSESSMENT", 0.85)
    print("Initial state: python STRONG, statistics GAP, ml_fundamentals GAP,")
    print("supervised_learning met, model_evaluation UNKNOWN, deployment UNKNOWN.")

    v1 = make_path(uid)
    show_path(v1, "PATH V1")

    first = next(i for i in v1["items"] if i["executable"] and i["kind"] == "EXECUTABLE")
    client.post(
        f"/v1/learners/{uid}/paths/{v1['id']}/complete-item",
        json={"position": first["position"]},
    ).raise_for_status()
    print(f"Completed week-1 work: pos{first['position']} {first['resource']}")

    body = submit(uid, "model-evaluation-gate", wrong("model-evaluation-gate"))
    print(f"Assessment: overall={body['overall_score']:.2f} passed={body['passed']}")
    for result in body["skill_results"]:
        print(
            f"  {result['skill']}: observed={result['observed_level']:.2f} "
            f"confidence={result['confidence']:.2f}"
        )
    print(f"adaptation: {body['adaptation']} -> path_v2={body['path_id']}")

    v2 = next(p for p in client.get(f"/v1/learners/{uid}/paths").json() if p["id"] == body["path_id"])
    show_path(v2, "PATH V2")
    show_diff(body["diff"])

    gaps = client.get(f"/v1/learners/{uid}/roles/{AIML}/gaps").json()["items"]
    deployment = next(i for i in gaps if i["skill"] == "model_deployment")
    print(
        f"Downstream check: model_deployment action={deployment['action']} "
        f"blockers={deployment['blockers']}"
    )


def scenario_positive() -> None:
    banner("SCENARIO B (positive surprise): strong assessment removes remediation")
    uid = learner(f"demo-b-{uuid.uuid4().hex[:6]}")
    evidence(uid, "python", "ASSESSMENT", 0.90)
    evidence(uid, "statistics", "SELF_REPORT", 0.45, confidence=0.60)
    evidence(uid, "ml_fundamentals", "ASSESSMENT", 0.55)
    v1 = make_path(uid)
    show_path(v1, "PATH V1")

    body = submit(uid, "statistics-gate", correct("statistics-gate"))
    print(f"Assessment: overall={body['overall_score']:.2f} passed={body['passed']}")
    print(f"adaptation: {body['adaptation']} -> path_v2={body['path_id']}")
    v2 = next(p for p in client.get(f"/v1/learners/{uid}/paths").json() if p["id"] == body["path_id"])
    show_path(v2, "PATH V2")
    show_diff(body["diff"])


def scenario_unknown() -> None:
    banner("SCENARIO C (UNKNOWN -> KNOWN): docker gate resolves, resource unblocks")
    uid = learner(f"demo-c-{uuid.uuid4().hex[:6]}")
    evidence(uid, "python", "ASSESSMENT", 0.92)
    evidence(uid, "statistics", "ASSESSMENT", 0.85)
    evidence(uid, "ml_fundamentals", "ASSESSMENT", 0.88)
    evidence(uid, "model_evaluation", "ASSESSMENT", 0.85)
    evidence(uid, "model_deployment", "ASSESSMENT", 0.30)
    evidence(uid, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = make_path(uid)
    show_path(v1, "PATH V1")

    suggested = client.get(f"/v1/learners/{uid}/roles/{AIML}/assessments/suggested").json()
    print(f"Suggested assessment: {suggested['assessment']} covers={suggested['covers']}")

    body = submit(uid, "docker-gate", correct("docker-gate"))
    print(f"Assessment: overall={body['overall_score']:.2f} passed={body['passed']}")
    print(f"adaptation: {body['adaptation']} -> path_v2={body['path_id']}")
    v2 = next(p for p in client.get(f"/v1/learners/{uid}/paths").json() if p["id"] == body["path_id"])
    show_path(v2, "PATH V2")
    show_diff(body["diff"])


def scenario_conflict() -> None:
    banner("SCENARIO D (conflict): self-report 0.90 vs assessment 0.50")
    uid = learner(f"demo-d-{uuid.uuid4().hex[:6]}")
    evidence(uid, "python", "SELF_REPORT", 0.90)
    make_path(uid)
    body = submit(uid, "python-gate", [1, 0, 0])
    print(f"Assessment: overall={body['overall_score']:.2f} passed={body['passed']}")
    skills = client.get(f"/v1/learners/{uid}/skills").json()
    python = next(i for i in skills if i["skill"] == "python")
    print(
        f"Fused python: proficiency={python['proficiency']:.2f} conflict={python['conflict']} "
        f"evidence_count={python['evidence_count']} dominant={python['dominant_source']}"
    )
    print(f"reason: {python['reason']}")


def scenario_freeze() -> None:
    banner("SCENARIO E (freeze): completed weeks frozen while later work changes")
    uid = learner(f"demo-e-{uuid.uuid4().hex[:6]}")
    evidence(uid, "python", "ASSESSMENT", 0.90)
    evidence(uid, "statistics", "ASSESSMENT", 0.35)
    evidence(uid, "ml_fundamentals", "ASSESSMENT", 0.55)
    evidence(uid, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = make_path(uid)
    executable = [i for i in v1["items"] if i["executable"] and i["kind"] == "EXECUTABLE"]
    for item in executable[:2]:
        client.post(
            f"/v1/learners/{uid}/paths/{v1['id']}/complete-item",
            json={"position": item["position"]},
        ).raise_for_status()
        print(f"Completed: pos{item['position']} week {item['week']} {item['resource']}")

    body = submit(uid, "model-evaluation-gate", wrong("model-evaluation-gate"))
    print(f"adaptation: {body['adaptation']}")
    v2 = next(p for p in client.get(f"/v1/learners/{uid}/paths").json() if p["id"] == body["path_id"])
    show_path(v2, "PATH V2 (completed rows must keep position + week)")
    show_diff(body["diff"])


if __name__ == "__main__":
    scenario_primary()
    scenario_positive()
    scenario_unknown()
    scenario_conflict()
    scenario_freeze()
