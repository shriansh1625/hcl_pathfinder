"""Deterministic assessment definition fingerprint for drift detection.

YAML is the seed source; the database is the runtime authority after seed.
A canonical JSON representation is hashed with SHA-256 so seed-time and
runtime-time definitions can be compared without silent drift.
"""

from __future__ import annotations

import hashlib
import json

from app.ontology.load import AssessmentSpec, QuestionSpec


def _canonical_question(position: int, question: QuestionSpec) -> dict:
    return {
        "position": position,
        "skill": question.skill,
        "difficulty": question.difficulty,
        "choices": list(question.choices),
        "correct_index": question.correct_index,
        "concept_tag": question.concept_tag,
    }


def canonical_assessment_dict(spec: AssessmentSpec) -> dict:
    """Normalized assessment payload — prompts excluded (scoring uses structure only)."""
    questions = [
        _canonical_question(index, question)
        for index, question in enumerate(spec.questions)
    ]
    return {
        "slug": spec.slug,
        "primary_skill": spec.primary_skill,
        "pass_threshold": round(spec.pass_threshold, 6),
        "target_role": spec.target_role,
        "target_skills": sorted(spec.target_skills),
        "questions": questions,
    }


def assessment_fingerprint(spec: AssessmentSpec) -> str:
    payload = canonical_assessment_dict(spec)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
