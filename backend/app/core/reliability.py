"""Evidence reliability — prototype assumptions, not immutable truths.

Loaded from data/ontology/reliability.yaml so later engines can change
weights without rewriting domain logic.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.core.enums import EvidenceSource
from app.core.paths import DATA_DIR


@lru_cache(maxsize=1)
def load_reliability() -> dict[str, float]:
    path = DATA_DIR / "ontology" / "reliability.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = payload["sources"]
    return {str(k): float(v) for k, v in sources.items()}


def reliability_for(source: EvidenceSource | str) -> float:
    key = source.value if isinstance(source, EvidenceSource) else str(source)
    table = load_reliability()
    if key not in table:
        raise KeyError(f"No reliability configured for evidence source {key}")
    return table[key]
