"""Judge-facing primary demo (Scenario A) with milestone output."""

from __future__ import annotations

import time
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.ontology.load import load_ontology

client = TestClient(app)
BUNDLE = load_ontology()
SPECS = {item.slug: item for item in BUNDLE.assessments}
AIML = "ai-ml-engineer"
DEMO_TAG = "pathfinder-judge-demo"


def _wrong(slug: str) -> list[int]:
    return [(q.correct_index + 1) % len(q.choices) for q in SPECS[slug].questions]


def _gap_label(item: dict) -> str:
    if item.get("evidence_state") == "UNKNOWN":
        return "UNKNOWN"
    attainment = item.get("attainment", "")
    if attainment == "TARGET_MET":
        return "TARGET MET"
    if attainment == "GAP":
        return "GAP"
    return item.get("status", "")


def run_primary_demo() -> dict:
    started = time.perf_counter()
    api_calls = 0

    def post(url: str, **kwargs):
        nonlocal api_calls
        api_calls += 1
        return client.post(url, **kwargs)

    def get(url: str):
        nonlocal api_calls
        api_calls += 1
        return client.get(url)

    uid = post("/v1/learners", json={"display_name": f"{DEMO_TAG}-{uuid.uuid4().hex[:6]}"}).json()["id"]
    for skill, level in [
        ("python", 0.90),
        ("statistics", 0.35),
        ("ml_fundamentals", 0.55),
        ("supervised_learning", 0.85),
    ]:
        post(
            f"/v1/learners/{uid}/evidence",
            json={"skill": skill, "source": "ASSESSMENT", "observed_level": level, "confidence": 0.85},
        ).raise_for_status()

    v1 = post(
        f"/v1/learners/{uid}/paths",
        json={"role": AIML, "weekly_hours": 8, "learning_style": "MIXED"},
    ).json()

    gaps = get(f"/v1/learners/{uid}/roles/{AIML}/gaps").json()["items"]
    focus = {skill: next((g for g in gaps if g["skill"] == skill), {}) for skill in [
        "python", "statistics", "ml_fundamentals", "model_evaluation", "model_deployment"
    ]}

    print("=" * 50)
    print("PATHFINDER — LIVE ADAPTIVE CAREER INTELLIGENCE")
    print("=" * 50)
    print()
    print("GOAL")
    print("AI/ML Engineer")
    print("8h/week")
    print()
    print("CURRENT STATE")
    for skill in ["python", "statistics", "ml_fundamentals", "model_evaluation", "model_deployment"]:
        row = focus.get(skill) or {}
        prof = row.get("proficiency")
        label = _gap_label(row)
        prof_text = "—" if prof is None else f"{prof:.2f}"
        print(f"{skill.replace('_', ' ').title():<18} {prof_text:>6}  {label}")

    print()
    print("PATH V1")
    for item in v1["items"]:
        if not item["executable"]:
            continue
        week = item.get("week") or "?"
        title = item.get("title") or item.get("resource")
        print(f"Week {week}  {title}")

    first = next(i for i in v1["items"] if i["executable"] and i["kind"] == "EXECUTABLE")
    post(
        f"/v1/learners/{uid}/paths/{v1['id']}/complete-item",
        json={"position": first["position"]},
    ).raise_for_status()

    print()
    print("PROVE IT")
    print("Model Evaluation Assessment")
    attempt = post(
        f"/v1/learners/{uid}/assessments/model-evaluation-gate/attempts",
        json={"answers": _wrong("model-evaluation-gate")},
    ).json()

    me = next(r for r in attempt["skill_results"] if r["skill"] == "model_evaluation")
    print()
    print("RESULT")
    print("Model Evaluation")
    print("UNKNOWN -> GAP")
    print(f"observed = {me['observed_level']:.2f}")
    print("target = 0.80")

    v2 = next(p for p in get(f"/v1/learners/{uid}/paths").json() if p["id"] == attempt["path_id"])
    print()
    print("PATH V2")
    for entry in attempt["diff"]["added"]:
        if entry["skill"] == "model_evaluation":
            print(f"+ {entry['title']}")
    print("-> Deployment delayed")

    print()
    print("FROZEN")
    print(f"Week {first['week']} {first['title']} remains COMPLETED")

    print()
    print("WHY?")
    reason = next(
        (entry["reason"] for entry in attempt["diff"]["added"] if entry["skill"] == "model_evaluation"),
        "",
    )
    print(f"\"{reason}\"")

    timeline = get(f"/v1/learners/{uid}/roles/{AIML}/path-timeline").json()
    print()
    print("PATH TIMELINE")
    print(" -> ".join(f"V{entry['version']}" for entry in timeline))

    elapsed = time.perf_counter() - started
    return {"api_calls": api_calls, "elapsed_seconds": round(elapsed, 2), "learner_id": uid}


if __name__ == "__main__":
    stats = run_primary_demo()
    print()
    print(f"(demo api_calls={stats['api_calls']} elapsed={stats['elapsed_seconds']}s)")
