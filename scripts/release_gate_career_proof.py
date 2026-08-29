"""Multi-career path isolation proof — same learner, different roles, backend-driven."""

from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.request

BASE = os.environ.get("PATHFINDER_API_URL") or os.environ.get("PF_API_URL")
if not BASE:
    print("Set PATHFINDER_API_URL", file=sys.stderr)
    sys.exit(2)
ROLES = ["ai-ml-engineer", "cybersecurity-analyst", "backend-developer"]


def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get(path: str) -> dict | list:
    with urllib.request.urlopen(f"{BASE}{path}") as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    learner = post("/v1/learners", {"display_name": f"career-proof-{uuid.uuid4().hex[:8]}"})
    learner_id = learner["id"]

    # Seed once with AI/ML demo evidence — diagnosis must differ by role, not by re-seeding.
    for row in get("/v1/roles/ai-ml-engineer/demo-evidence"):
        post(
            f"/v1/learners/{learner_id}/evidence",
            {
                "skill": row["skill"],
                "source": row["source"],
                "observed_level": row["observed_level"],
                "confidence": row["confidence"],
            },
        )

    snapshots: dict[str, dict] = {}
    for role in ROLES:
        path = post(
            f"/v1/learners/{learner_id}/paths",
            {"role": role, "weekly_hours": 8, "learning_style": "MIXED"},
        )
        gaps = get(f"/v1/learners/{learner_id}/roles/{role}/gaps")
        top = sorted(gaps["items"], key=lambda item: item["action_priority"], reverse=True)[:5]
        snapshots[role] = {
            "top_gaps": [item["skill"] for item in top],
            "path_skills": [item["target_skill"] for item in path["items"][:8]],
            "path_count": len(path["items"]),
        }

    aiml = snapshots["ai-ml-engineer"]
    cyber = snapshots["cybersecurity-analyst"]
    backend = snapshots["backend-developer"]

    checks = [
        ("aiml vs cyber gaps differ", aiml["top_gaps"] != cyber["top_gaps"]),
        ("aiml vs backend gaps differ", aiml["top_gaps"] != backend["top_gaps"]),
        ("aiml vs cyber paths differ", aiml["path_skills"] != cyber["path_skills"]),
        ("aiml vs backend paths differ", aiml["path_skills"] != backend["path_skills"]),
        ("cyber vs backend paths differ", cyber["path_skills"] != backend["path_skills"]),
    ]

    print(json.dumps(snapshots, indent=2))
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print(json.dumps({"passed": len(checks), "total": len(checks)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
