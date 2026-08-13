"""Stable ontology identifiers.

YAML slugs are the human-facing keys. Database primary keys are UUIDv5
derived from slug so seed is idempotent and IDs stay stable across machines.
"""

from __future__ import annotations

import uuid

ONTOLOGY_NAMESPACE = uuid.UUID("6b1c0a0e-4f3a-4c8e-9d2b-7a1e5c3f8d21")


def ontology_uuid(kind: str, slug: str) -> uuid.UUID:
    return uuid.uuid5(ONTOLOGY_NAMESPACE, f"{kind}:{slug}")
