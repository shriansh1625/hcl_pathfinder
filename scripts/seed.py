"""Load YAML ontology, validate, and upsert into Postgres. Idempotent."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.seed import seed_ontology  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.ontology.load import load_ontology  # noqa: E402
from app.ontology.validate import validate_ontology  # noqa: E402


def main() -> int:
    bundle = load_ontology()
    errors = validate_ontology(bundle)
    if errors:
        print("Ontology validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    session = SessionLocal()
    try:
        seed_ontology(session, bundle)
    finally:
        session.close()

    print(
        "Seed complete:",
        f"{len(bundle.skills)} skills,",
        f"{len(bundle.roles)} roles,",
        f"{len(bundle.relationships)} relationships,",
        f"{len(bundle.resources)} resources,",
        f"{len(bundle.assessments)} assessments.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
