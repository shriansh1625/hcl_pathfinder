"""Smoke-test documented public API endpoints."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("PATHFINDER_API_URL") or os.environ.get("PF_API_URL")
if not BASE:
    print("Set PATHFINDER_API_URL (example: http://127.0.0.1:8000)", file=sys.stderr)
    raise SystemExit(2)


def get(path: str) -> tuple[int, dict | list | str]:
    try:
        with urllib.request.urlopen(f"{BASE}{path}") as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def post(path: str, payload: dict) -> tuple[int, dict | list | str]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    for path in ["/health", "/ready", "/v1/roles", "/v1/meta/ontology"]:
        code, _ = get(path)
        checks.append((path, code == 200, f"status={code}"))

    code, intake = post(
        "/v1/intake/goal",
        {"goal": "I want to become a machine learning engineer focused on production systems."},
    )
    checks.append(("POST /v1/intake/goal", code == 200 and isinstance(intake, dict), f"status={code}"))

    code, learner = post(
        "/v1/learners",
        {
            "display_name": f"smoke-{uuid.uuid4().hex[:8]}",
            "experience_level": "INTERMEDIATE",
            "weekly_hours": 8,
            "learning_style": "MIXED",
            "target_role": "ai-ml-engineer",
        },
    )
    learner_id = learner.get("id") if isinstance(learner, dict) else None
    checks.append(("POST /v1/learners", code == 200 and bool(learner_id), f"status={code}"))

    if learner_id:
        code, _ = post(
            f"/v1/learners/{learner_id}/evidence",
            {"skill": "python", "source": "ASSESSMENT", "observed_level": 0.7, "confidence": 0.85},
        )
        checks.append(("POST /v1/learners/{id}/evidence", code == 200, f"status={code}"))

        code, gaps = get(f"/v1/learners/{learner_id}/roles/ai-ml-engineer/gaps")
        checks.append(("GET /v1/learners/{id}/roles/{role}/gaps", code == 200, f"status={code}"))

        code, path = post(
            f"/v1/learners/{learner_id}/paths",
            {"role": "ai-ml-engineer", "weekly_hours": 8, "learning_style": "MIXED"},
        )
        path_id = path.get("id") if isinstance(path, dict) else None
        checks.append(("POST /v1/learners/{id}/paths", code == 200 and bool(path_id), f"status={code}"))

        if path_id and isinstance(path, dict) and path.get("items"):
            item = next((row for row in path["items"] if row.get("executable")), path["items"][0])
            code, _ = post(
                f"/v1/learners/{learner_id}/progress",
                {
                    "path_id": path_id,
                    "position": item["position"],
                    "outcome": "STRUGGLED",
                    "self_reported_level": 0.2,
                },
            )
            checks.append(("POST /v1/learners/{id}/progress", code == 200, f"status={code}"))

        code, _ = get(f"/v1/learners/{learner_id}/roles/ai-ml-engineer/dashboard")
        checks.append(("GET /v1/learners/{id}/roles/{role}/dashboard", code == 200, f"status={code}"))

        code, _ = get(f"/v1/learners/{learner_id}/roles/ai-ml-engineer/path-timeline")
        checks.append(("GET /v1/learners/{id}/roles/{role}/path-timeline", code == 200, f"status={code}"))

        code, _ = post(
            f"/v1/learners/{learner_id}/ai/explain",
            {"intent": "WHY_RESOURCE", "skill": "python"},
        )
        checks.append(("POST /v1/learners/{id}/ai/explain", code in (200, 503), f"status={code}"))

        code, _ = get("/v1/assessments/python-gate")
        checks.append(("GET /v1/assessments/{slug}", code == 200, f"status={code}"))

    _, meta = get("/v1/meta/ontology")
    if isinstance(meta, dict):
        expected = {"skills": 47, "roles": 8, "skill_relationships": 58, "resources": 62, "assessments": 4}
        for key, val in expected.items():
            actual = meta.get(key)
            checks.append((f"ontology {key}", actual == val, f"expected={val} actual={actual}"))

    failed = [row for row in checks if not row[1]]
    for path, ok, detail in checks:
        print(("PASS" if ok else "FAIL"), path, detail)
    print(json.dumps({"passed": len(checks) - len(failed), "total": len(checks), "base": BASE}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
