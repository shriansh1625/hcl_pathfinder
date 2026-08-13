"""Validate ontology YAML without touching the database."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.ontology.load import load_ontology  # noqa: E402
from app.ontology.validate import hard_prerequisite_cycles, validate_ontology  # noqa: E402


def main() -> int:
    bundle = load_ontology()
    errors = validate_ontology(bundle)
    cycles = hard_prerequisite_cycles(bundle)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK")
    print(f"  skills={len(bundle.skills)}")
    print(f"  roles={len(bundle.roles)}")
    print(f"  relationships={len(bundle.relationships)}")
    print(f"  hard_cycles={len(cycles)}")
    print(f"  resources={len(bundle.resources)}")
    print(f"  assessments={len(bundle.assessments)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
