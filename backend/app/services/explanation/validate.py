"""Reject LLM output that invents entities, numbers, or uncited claims."""

from __future__ import annotations

import re

from app.ontology.load import load_ontology
from app.services.explanation.schema import AIContext, GroundedAnswer

_NUMBER = re.compile(r"\b(?:0?\.\d{1,4}|\d\.\d{1,4}|\d{1,3}%)\b")
_SLUG = re.compile(r"\b[a-z][a-z0-9]+(?:_[a-z0-9]+)+\b")
_PROFICIENCY_CLAIM = re.compile(r"\b(?:proficiency|mastered|mastery)\b[^.]{0,40}?\b(\d(?:\.\d+)?)\b", re.I)
_REQUIREMENT = re.compile(r"\b(?:need|require|requires|requiring|missing prerequisite)\s+([a-z][a-z0-9_-]+)", re.I)


class ValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _mentions_token(answer: str, token: str) -> bool:
    if not token:
        return False
    return bool(re.search(rf"(?<![a-z0-9_-]){re.escape(token)}(?![a-z0-9_-])", answer))


def validate_answer(raw: GroundedAnswer, context: AIContext) -> GroundedAnswer:
    known_facts = context.fact_ids()
    if not raw.answer.strip():
        raise ValidationError("empty_answer", "Empty model answer")
    if raw.confidence != "grounded":
        raise ValidationError("bad_confidence", "confidence must be grounded")
    if not raw.claims:
        raise ValidationError("no_claims", "No claims returned")
    for claim in raw.claims:
        if not claim.fact_ids:
            raise ValidationError("uncited_claim", "Claim missing fact_ids")
        unknown = [fid for fid in claim.fact_ids if fid not in known_facts]
        if unknown:
            raise ValidationError("unknown_fact", f"Unknown fact ids: {unknown}")

    _reject_unknown_skills(raw.answer, context)
    _reject_unknown_resources(raw.answer, context)
    _reject_unknown_roles(raw.answer, context)
    _reject_unsupported_numbers(raw.answer, context)
    _reject_proficiency_claims(raw.answer, context)
    _reject_invented_requirements(raw.answer, context)
    _reject_external_claims(raw.answer)
    _reject_override_language(raw.answer)
    return raw.model_copy(update={"facts": context.facts, "intent": context.intent, "confidence": "grounded"})


def _reject_unknown_skills(answer: str, context: AIContext) -> None:
    bundle = load_ontology()
    allowed = {slug.lower() for slug in context.allowed_skills}
    allowed_names = {item.lower() for item in context.allowed_titles}
    lowered = answer.lower()
    for skill in bundle.skills:
        slug = skill.slug.lower()
        name = skill.canonical_name.lower()
        if slug in allowed or name in allowed_names:
            continue
        if _mentions_token(lowered, slug) or (len(name) > 4 and _mentions_token(lowered, name)):
            raise ValidationError("unsupported_skill", f"Unsupported skill: {skill.slug}")
    for slug in _SLUG.findall(lowered):
        if any(skill.slug == slug for skill in bundle.skills) and slug not in allowed:
            raise ValidationError("unsupported_skill", f"Unsupported skill slug: {slug}")


def _reject_unknown_resources(answer: str, context: AIContext) -> None:
    bundle = load_ontology()
    allowed_slugs = {slug.lower() for slug in context.allowed_resources}
    allowed_titles = {title.lower() for title in context.allowed_titles}
    lowered = answer.lower()
    for resource in bundle.resources:
        slug = resource.slug.lower()
        title = resource.title.lower()
        if slug in allowed_slugs or title in allowed_titles:
            continue
        if (
            _mentions_token(lowered, slug)
            or slug.replace("-", " ") in lowered
            or (len(title) > 8 and title in lowered)
        ):
            raise ValidationError("unsupported_resource", f"Unsupported resource: {resource.slug}")


def _reject_unknown_roles(answer: str, context: AIContext) -> None:
    bundle = load_ontology()
    allowed = {slug.lower() for slug in context.allowed_roles}
    allowed_names = {item.lower() for item in context.allowed_titles}
    for role in bundle.roles:
        if role.slug.lower() in allowed or role.name.lower() in allowed_names:
            continue
        if role.slug.lower() in answer.lower() or role.name.lower() in answer.lower():
            raise ValidationError("unsupported_role", f"Unsupported role: {role.slug}")


def _reject_unsupported_numbers(answer: str, context: AIContext) -> None:
    allowed = set(context.allowed_numbers)
    for raw in _NUMBER.findall(answer):
        if raw.endswith("%"):
            value = round(int(raw[:-1]) / 100.0, 4)
        else:
            value = round(float(raw), 4)
        if not any(abs(value - item) < 1e-3 for item in allowed):
            if raw.endswith("%") or "." in raw or raw.startswith("0"):
                raise ValidationError("unsupported_number", f"Unsupported number: {raw}")


def _reject_proficiency_claims(answer: str, context: AIContext) -> None:
    allowed = set(context.allowed_numbers)
    attainment = next((item.value for item in context.facts if item.id == "skill.attainment"), "")
    lowered = answer.lower()
    for match in _PROFICIENCY_CLAIM.finditer(answer):
        value = round(float(match.group(1)), 4)
        if not any(abs(value - item) < 1e-3 for item in allowed):
            raise ValidationError("unsupported_number", f"Unsupported proficiency claim: {match.group(1)}")
    for raw in _NUMBER.findall(answer):
        if raw.endswith("%"):
            continue
        value = round(float(raw), 4)
        if value > 0 and value <= 1 and not any(abs(value - item) < 1e-3 for item in allowed):
            if any(token in lowered for token in ("proficiency", "mastered", "mastery", "expert", "target")):
                raise ValidationError("unsupported_number", f"Unsupported proficiency-like number: {raw}")
    if attainment != "TARGET_MET" and any(
        phrase in lowered
        for phrase in (
            "already mastered",
            "you already mastered",
            "you are already an expert",
            "proficiency 1.0",
            "proficiency 1 ",
        )
    ):
        raise ValidationError("override_attempt", "Unsupported mastery claim")
    if attainment == "TARGET_MET" and any(
        phrase in lowered for phrase in ("proficiency 1.0", "proficiency 1 ", "already mastered", "you already mastered")
    ):
        raise ValidationError("override_attempt", "Unsupported mastery claim")


def _reject_invented_requirements(answer: str, context: AIContext) -> None:
    bundle = load_ontology()
    allowed_skills = {slug.lower() for slug in context.allowed_skills}
    allowed_resources = {slug.lower() for slug in context.allowed_resources}
    ontology_skills = {item.slug.lower() for item in bundle.skills}
    ontology_resources = {item.slug.lower() for item in bundle.resources}
    fact_ids = context.fact_ids()
    prereq_facts = {item.removeprefix("prereq.") for item in fact_ids if item.startswith("prereq.")}
    lowered = answer.lower()
    if "prerequisite" in lowered:
        for slug in _SLUG.findall(lowered):
            if slug in ontology_skills and slug not in prereq_facts:
                raise ValidationError("unsupported_skill", f"Unsupported prerequisite claim: {slug}")
    for match in _REQUIREMENT.finditer(lowered):
        token = match.group(1).replace("-", "_")
        if token in allowed_skills or token in allowed_resources:
            continue
        if token in ontology_skills or token in ontology_resources:
            raise ValidationError("unsupported_skill", f"Unsupported requirement: {token}")
        if len(token) >= 4 and token not in {"this", "that", "more", "your", "path", "role", "week"}:
            raise ValidationError("unsupported_skill", f"Invented requirement: {token}")


def _reject_external_claims(answer: str) -> None:
    lowered = answer.lower()
    banned = (
        "salary impact",
        "employers currently require",
        "industry salary",
        "$",
        "even if the backend",
        "ignore pathfinder",
        "invent prerequisites",
        "invent prerequisite",
        "invented a better roadmap",
        "instead of the assigned",
        "instead of your assigned",
        "absolutely required for this role even if",
        "three other courses",
        "give me three other courses",
    )
    if any(item in lowered for item in banned):
        raise ValidationError("unsupported_claim", "Unsupported external or invented claim")


def _reject_override_language(answer: str) -> None:
    lowered = answer.lower()
    banned = (
        "i changed your proficiency",
        "proficiency is now 1",
        "you are already an expert",
        "i added a course",
        "i created a new skill",
        "i updated your path",
        "i invented a",
        "invented a course",
    )
    if any(item in lowered for item in banned):
        raise ValidationError("override_attempt", "Model attempted to mutate learner state")
