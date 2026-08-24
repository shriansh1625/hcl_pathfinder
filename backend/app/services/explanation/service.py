"""Orchestrate grounded explanation. Deterministic core never waits on this module."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.services.explanation.cache import cache_get, cache_set
from app.services.explanation.builder import build_context
from app.services.explanation.fallback import explain_deterministic
from app.services.explanation.provider import AIProvider, ProviderError, get_provider
from app.services.explanation.schema import GroundedAnswer, Intent
from app.services.explanation.validate import ValidationError, validate_answer

_provider: AIProvider | None = None


def set_provider(provider: AIProvider | None) -> None:
    global _provider
    _provider = provider


def active_provider() -> AIProvider:
    return _provider or get_provider()


def explain(
    session: Session,
    *,
    user_id: UUID,
    intent: Intent,
    skill: str | None = None,
    resource: str | None = None,
    query: str | None = None,
) -> GroundedAnswer:
    context = build_context(
        session,
        user_id=user_id,
        intent=intent,
        skill_slug=skill,
        resource_slug=resource,
        query=query,
    )
    cached = cache_get(context.fingerprint)
    if cached is not None:
        return cached

    fallback = explain_deterministic(context, query)
    try:
        raw = (
            active_provider().answer_grounded_query(context, query or "")
            if intent == "QUERY" or query
            else active_provider().generate_explanation(context, query)
        )
        validated = validate_answer(raw, context)
        validated = validated.model_copy(update={"source": "llm", "facts": context.facts, "intent": context.intent})
        cache_set(context.fingerprint, validated)
        return validated
    except (ProviderError, ValidationError):
        return fallback
