"""Role-specific demo evidence."""

from __future__ import annotations

from pathlib import Path

import yaml

_DEMO_PATH = Path(__file__).resolve().parents[4] / "data" / "demo" / "evidence_by_role.yaml"


def load_demo_evidence(role_slug: str) -> list[dict]:
    if not _DEMO_PATH.exists():
        return []
    payload = yaml.safe_load(_DEMO_PATH.read_text(encoding="utf-8")) or {}
    rows = payload.get("roles", {}).get(role_slug, [])
    return [
        {
            "skill": row["skill"],
            "observed_level": float(row["observed_level"]),
            "source": row.get("source", "ASSESSMENT"),
            "confidence": float(row.get("confidence", 0.85)),
        }
        for row in rows
    ]
