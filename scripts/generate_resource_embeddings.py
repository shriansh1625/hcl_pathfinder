#!/usr/bin/env python3
"""Generate offline catalog resource embeddings for PathFinder semantic relevance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.ontology.load import load_ontology
from app.services.retrieval.embeddings import build_resource_document, skill_name_map

MODEL = "BAAI/bge-small-en-v1.5"
OUTPUT = REPO_ROOT / "data" / "catalog" / "resource_embeddings.json"


def main() -> None:
    from fastembed import TextEmbedding

    bundle = load_ontology()
    names = skill_name_map(bundle)
    active = [resource for resource in bundle.resources if resource.is_active]
    documents = [
        (resource.slug, build_resource_document(resource, skill_names=names))
        for resource in active
    ]

    model = TextEmbedding(model_name=MODEL)
    vectors = list(model.embed(document for _, document in documents))
    if not vectors:
        raise SystemExit("No embeddings were generated.")

    payload = {
        "model": MODEL,
        "dimensions": len(vectors[0]),
        "resources": {
            slug: [float(value) for value in vector]
            for (slug, _), vector in zip(documents, vectors, strict=True)
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(payload['resources'])} embeddings ({payload['dimensions']}d) to {OUTPUT}")


if __name__ == "__main__":
    main()
