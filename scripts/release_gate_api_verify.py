"""Verify release-gate API endpoints against canonical backend."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("PATHFINDER_API_URL") or os.environ.get("PF_API_URL")
if not BASE:
    print("Set PATHFINDER_API_URL (example: http://127.0.0.1:8000)", file=sys.stderr)
    sys.exit(2)


def get(path: str) -> tuple[int, dict | list | str]:
    try:
        with urllib.request.urlopen(f"{BASE}{path}") as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def post(path: str, payload: dict) -> tuple[int, dict | str]:
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
        return exc.code, exc.read().decode()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    for path in ["/health", "/ready", "/v1/roles", "/v1/meta/ontology"]:
        code, body = get(path)
        ok = code == 200
        checks.append((path, ok, f"status={code}"))

    for role in ["ai-ml-engineer", "backend-developer"]:
        code, _ = get(f"/v1/roles/{role}/competencies")
        checks.append((f"GET /v1/roles/{role}/competencies", code == 200, f"status={code}"))
        code, _ = get(f"/v1/roles/{role}/demo-evidence")
        checks.append((f"GET /v1/roles/{role}/demo-evidence", code == 200, f"status={code}"))

    code, body = post("/v1/intake/goal", {"goal": "I want to become a backend engineer within 12 months."})
    ok = code == 200 and isinstance(body, dict) and body.get("role")
    checks.append(("POST /v1/intake/goal", ok, f"status={code}"))

    _, meta = get("/v1/meta/ontology")
    if isinstance(meta, dict):
        expected = {"skills": 47, "roles": 8, "skill_relationships": 58, "resources": 62, "assessments": 4}
        for key, val in expected.items():
            actual = meta.get(key)
            checks.append((f"ontology {key}", actual == val, f"expected={val} actual={actual}"))
        if meta.get("resources_total", 0) < meta.get("resources", 0):
            checks.append(("ontology resources_total", False, "total < active"))

    failed = [c for c in checks if not c[1]]
    for path, ok, detail in checks:
        print(("PASS" if ok else "FAIL"), path, detail)
    print(json.dumps({"passed": len(checks) - len(failed), "total": len(checks)}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
