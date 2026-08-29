"""Natural-language goal intake.

Read-only: it interprets prose and returns a proposal. Nothing is persisted
until the learner confirms and the existing learner / evidence / path
endpoints are called, so a misread sentence can never write bad evidence.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.intelligence import (
    GoalIntakeCreate,
    GoalIntakeRead,
    ResolvedEntityRead,
    SkillClaimRead,
)
from app.services.intake.extract import GoalIntake, SkillClaim, parse_goal
from app.services.intake.resolver import ResolvedEntity

router = APIRouter(prefix="/v1")


def _entity(entity: ResolvedEntity) -> ResolvedEntityRead:
    return ResolvedEntityRead(
        slug=entity.slug, name=entity.name, mention=entity.mention, how=entity.how
    )


def _claim(claim: SkillClaim) -> SkillClaimRead:
    return SkillClaimRead(
        skill=claim.skill,
        name=claim.name,
        observed_level=round(claim.observed_level, 4),
        mention=claim.mention,
        level_phrase=claim.level_phrase,
        how=claim.how,
    )


def _read(result: GoalIntake) -> GoalIntakeRead:
    return GoalIntakeRead(
        goal_text=result.goal_text,
        role=_entity(result.role) if result.role else None,
        role_alternatives=[_entity(item) for item in result.role_alternatives],
        skills=[_claim(item) for item in result.skills],
        ungraded=[_claim(item) for item in result.ungraded],
        weekly_hours=result.weekly_hours,
        timeframe_weeks=result.timeframe_weeks,
        learning_style=result.learning_style,
        unresolved=list(result.unresolved),
        source=result.source,
        provider=result.provider,
        model=result.model,
    )


@router.post("/intake/goal", response_model=GoalIntakeRead)
def interpret_goal(payload: GoalIntakeCreate) -> GoalIntakeRead:
    """Resolve a free-text career goal against the ontology."""
    goal = payload.goal.strip()
    try:
        return _read(parse_goal(goal))
    except Exception:
        from app.ontology.load import load_ontology
        from app.services.intake import resolver as intake_resolver

        vocab = intake_resolver.build_vocabulary(load_ontology())
        from app.services.intake.extract import _rule_based

        return _read(_rule_based(goal, vocab))
