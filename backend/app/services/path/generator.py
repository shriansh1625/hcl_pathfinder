"""Select, sequence, and pack a personalized path from a GapProfile."""

from __future__ import annotations

from app.core.enums import ActionClass, EligibilityStatus, PathItemKind
from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import GapProfile
from app.services.path.causality import attach_causes
from app.services.path.quality import validate_path
from app.services.recommendation.causality import (
    has_role_relevance,
    is_known_focal,
    is_selectable_skill,
    unblocks_focal,
)
from app.services.recommendation.config import load_recommendation_config
from app.services.recommendation.models import (
    LearnerPreferences,
    PlannedItem,
    PlannedPath,
    ScoredCandidate,
    gap_index,
)
from app.services.recommendation.scorer import score_candidates
from app.services.retrieval.structured import retrieve_candidates
from app.services.sequencing.topological import sequence_resources
from app.services.sequencing.weekly_packer import pack_weeks
from app.services.skill_graph.dependency import SkillEdge
from app.services.verification.gates import VerificationGate, build_gates


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
                and row.eligibility.status is EligibilityStatus.ELIGIBLE
                and blockers_ready(skill)
            ]
            extras.sort(key=lambda row: (-row.breakdown.final_score, row.resource.slug))
            if extras:
                try_add(extras[0])

    return selected[:max_items]


def _select_gates(
    profile: GapProfile,
    edges: list[SkillEdge],
    selected: list[ScoredCandidate],
    max_gates: int,
) -> list[VerificationGate]:
    """UNKNOWN role skills become gates. They do not compete with numeric gaps."""
    all_gates = build_gates(profile, edges, max_gates=max(max_gates, 16))
    if not any(is_known_focal(item) for item in profile.items):
        return all_gates[:max_gates]
    needed: set[str] = set()
    for gate in all_gates:
        if unblocks_focal(gate.skill_slug, profile):
            needed.add(gate.skill_slug)
    for row in selected:
        for check in row.eligibility.checks:
            if check.state.value == "UNKNOWN":
                needed.add(check.skill_slug)
    return [gate for gate in all_gates if gate.skill_slug in needed][:max_gates]


def _collect_waiting(
    selected: list[ScoredCandidate],
    scored: list[ScoredCandidate],
    packed: list[PlannedItem],
    gates: list[VerificationGate],
) -> list[ScoredCandidate]:
    waiting = [row for row in selected if row.eligibility.status is not EligibilityStatus.ELIGIBLE]
    seen = {row.resource.slug for row in selected}
    gated = {gate.skill_slug for gate in gates}
    covered = set()
    for item in packed:
        if item.candidate is None:
            continue
        for skill in item.candidate.resource.skills:
            if skill.coverage_strength >= 0.35:
                covered.add(skill.slug)
    extras: list[ScoredCandidate] = []
    for row in scored:
        if row.resource.slug in seen or not has_role_relevance(row):
            continue
        if row.eligibility.status is EligibilityStatus.BLOCKED_BY_UNKNOWN:
            unknown = {
                check.skill_slug
                for check in row.eligibility.checks
                if check.state.value == "UNKNOWN"
            }
            if unknown & gated:
                extras.append(row)
        elif row.eligibility.status is EligibilityStatus.BLOCKED_BY_KNOWN_GAP:
            missing = {
                check.skill_slug
                for check in row.eligibility.checks
                if check.state.value == "UNSATISFIED"
            }
            if missing & covered:
                extras.append(row)
    extras.sort(key=lambda row: row.resource.slug)
    for row in extras[:6]:
        waiting.append(row)
        seen.add(row.resource.slug)
    return waiting


def _waiting_kind(candidate: ScoredCandidate) -> str:
    if candidate.eligibility.status is EligibilityStatus.BLOCKED_BY_UNKNOWN:
        return PathItemKind.WAITING_FOR_VERIFICATION.value
    return PathItemKind.WAITING_FOR_REMEDIATION.value


def _gate_item(gate: VerificationGate, position: int, week: int) -> PlannedItem:
    return PlannedItem(
        candidate=None,
        position=position,
        week_index=week,
        kind=PathItemKind.VERIFICATION_GATE.value,
        executable=True,
        gate=gate,
    )


def _waiting_item(candidate: ScoredCandidate, position: int) -> PlannedItem:
    return PlannedItem(
        candidate=candidate,
        position=position,
        week_index=None,
        kind=_waiting_kind(candidate),
        executable=False,
    )


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
    executable = [
        row for row in selected if row.eligibility.status is EligibilityStatus.ELIGIBLE
    ]
    ordered = sequence_resources(executable, edges)
    packed = pack_weeks(ordered, prefs.weekly_hours)
    gates = _select_gates(profile, edges, selected, cfg.max_verification_gates)
    waiting = _collect_waiting(selected, scored, packed, gates)

    merged: list[PlannedItem] = []
    position = 0
    for week_offset, gate in enumerate(gates, start=1):
        merged.append(_gate_item(gate, position, week_offset))
        position += 1
    week_base = len(gates)
    for item in packed:
        week = item.week_index + week_base if item.week_index else week_base + 1
        merged.append(
            PlannedItem(
                candidate=item.candidate,
                position=position,
                week_index=week,
                kind=PathItemKind.EXECUTABLE.value,
                executable=True,
            )
        )
        position += 1
    for row in waiting:
        merged.append(_waiting_item(row, position))
        position += 1

    merged = attach_causes(merged, profile, edges)
    hours = round(
        sum(
            item.candidate.resource.duration_hours
            for item in merged
            if item.executable and item.candidate is not None
        ),
        4,
    )
    quality = validate_path(
        merged,
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
        items=tuple(merged),
        total_estimated_hours=hours,
        quality=quality.as_dict(),
    )
