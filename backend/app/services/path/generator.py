"""Select, sequence, and pack a personalized path from a GapProfile."""

from __future__ import annotations

from app.core.enums import ActionClass, EligibilityStatus
from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import GapProfile
from app.services.path.causality import attach_causes
from app.services.path.quality import validate_path
from app.services.recommendation.causality import has_role_relevance, is_selectable_skill
from app.services.recommendation.config import load_recommendation_config
from app.services.recommendation.models import LearnerPreferences, PlannedPath, ScoredCandidate, gap_index
from app.services.recommendation.scorer import score_candidates
from app.services.retrieval.structured import retrieve_candidates
from app.services.sequencing.topological import sequence_resources
from app.services.sequencing.weekly_packer import pack_weeks
from app.services.skill_graph.dependency import SkillEdge


def _skill_order(profile: GapProfile) -> list[str]:
    ranked = sorted(profile.items, key=lambda item: (-item.action_priority, item.ranked.gap.skill_slug))
    return [
        item.ranked.gap.skill_slug
        for item in ranked
        if is_selectable_skill(item.ranked.gap.skill_slug, profile)
    ]


def _covers(candidate: ScoredCandidate, skill: str) -> bool:
    return any(item.slug == skill and item.coverage_strength >= 0.35 for item in candidate.resource.skills)


def _selection_wave(item, covered: set[str]) -> int:
    """Path selection is not diagnostic action_priority.

    Unblocked remediations first, then the skills they just unblocked,
    then reinforcement, then verification. Blocked skills stay last until
    their blockers are covered.
    """
    action = item.action
    if action is ActionClass.REMEDIATE:
        return 0
    if action is ActionClass.REMEDIATE_BLOCKER and set(item.gate.blockers) <= covered:
        return 1
    if action is ActionClass.REINFORCE:
        return 2
    if action is ActionClass.VERIFY:
        return 3
    if action is ActionClass.REMEDIATE_BLOCKER:
        return 4
    return 5


def select_for_path(
    scored: list[ScoredCandidate],
    profile: GapProfile,
    *,
    weekly_hours: float,
    max_items: int,
    horizon_weeks: int,
) -> list[ScoredCandidate]:
    budget = weekly_hours * horizon_weeks
    index = gap_index(profile)
    selected: list[ScoredCandidate] = []
    selected_slugs: set[str] = set()
    covered_skills: set[str] = set()
    used_hours = 0.0

    def try_add(candidate: ScoredCandidate) -> bool:
        nonlocal used_hours
        if candidate.resource.slug in selected_slugs:
            return False
        if not has_role_relevance(candidate):
            return False
        if used_hours + candidate.resource.duration_hours > budget + 1e-9:
            return False
        selected.append(candidate)
        selected_slugs.add(candidate.resource.slug)
        used_hours += candidate.resource.duration_hours
        for skill in candidate.resource.skills:
            if skill.coverage_strength >= 0.35:
                covered_skills.add(skill.slug)
        return True

    def blockers_ready(skill: str) -> bool:
        item = index.get(skill)
        if item is None or item.action is not ActionClass.REMEDIATE_BLOCKER:
            return True
        return set(item.gate.blockers) <= covered_skills

    pending = set(_skill_order(profile))
    while pending and len(selected) < max_items:
        ordered = sorted(
            pending,
            key=lambda skill: (
                _selection_wave(index[skill], covered_skills),
                -index[skill].action_priority,
                skill,
            ),
        )
        progressed = False
        for skill in ordered:
            if not blockers_ready(skill):
                continue
            options = sorted(
                [
                    row
                    for row in scored
                    if _covers(row, skill) and has_role_relevance(row)
                ],
                key=lambda row: (
                    0 if row.eligibility.status is EligibilityStatus.ELIGIBLE else 1,
                    0 if row.eligibility.status is not EligibilityStatus.BLOCKED_BY_KNOWN_GAP else 1,
                    -row.breakdown.final_score,
                    row.resource.slug,
                ),
            )
            if not options:
                pending.discard(skill)
                progressed = True
                break
            for pick in options:
                if try_add(pick):
                    break
            pending.discard(skill)
            progressed = True
            break
        if not progressed:
            break

    selected_skills = []
    for row in selected:
        if row.primary_skill not in selected_skills:
            selected_skills.append(row.primary_skill)
    for skill in selected_skills:
        if len(selected) >= max_items:
            break
        types_have = {row.resource.type for row in selected if _covers(row, skill)}
        for wanted in ("course", "lab", "project", "assessment"):
            if wanted in types_have or len(selected) >= max_items:
                continue
            extras = [
                row
                for row in scored
                if _covers(row, skill)
                and row.resource.type == wanted
                and has_role_relevance(row)
                and row.eligibility.status is not EligibilityStatus.BLOCKED_BY_KNOWN_GAP
                and blockers_ready(skill)
            ]
            extras.sort(key=lambda row: (-row.breakdown.final_score, row.resource.slug))
            if extras:
                try_add(extras[0])

    return selected[:max_items]


def generate_path(
    profile: GapProfile,
    catalog: list[ResourceSpec],
    edges: list[SkillEdge],
    prefs: LearnerPreferences,
) -> PlannedPath:
    cfg = load_recommendation_config()
    candidates = retrieve_candidates(profile, catalog)
    scored = score_candidates(candidates, profile, prefs)
    selected = select_for_path(
        scored,
        profile,
        weekly_hours=prefs.weekly_hours,
        max_items=cfg.max_items,
        horizon_weeks=cfg.horizon_weeks,
    )
    ordered = sequence_resources(selected, edges)
    packed = pack_weeks(ordered, prefs.weekly_hours)
    packed = attach_causes(packed, profile, edges)
    hours = round(sum(item.candidate.resource.duration_hours for item in packed), 4)
    quality = validate_path(
        packed,
        profile,
        catalog,
        edges,
        weekly_hours=prefs.weekly_hours,
    )
    return PlannedPath(
        role_slug=profile.role_slug,
        role_name=profile.role_name,
        weekly_hours=prefs.weekly_hours,
        learning_style=prefs.learning_style,
        items=tuple(packed),
        total_estimated_hours=hours,
        quality=quality.as_dict(),
    )
