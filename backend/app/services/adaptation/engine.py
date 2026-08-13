"""Adaptation engine: PATH V1 + new evidence → PATH V2.

Minimal mutation. Completed work is frozen. The learner model (fusion →
gap profile) causes every change; nothing is removed merely because an
assessment score was high.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import (
    AttainmentStatus,
    PathItemKind,
    PathItemStatus,
    PathItemType,
    ResourceType,
)
from app.ontology.load import ResourceSpec
from app.services.adaptation.diff import DiffEntry, PathDiff
from app.services.gap_engine.profile import GapProfile
from app.services.path.generator import generate_path
from app.services.recommendation.models import LearnerPreferences, PlannedItem
from app.services.skill_graph.dependency import SkillEdge


@dataclass(frozen=True)
class PathItemSnapshot:
    """Immutable view of a persisted V1 path item."""

    position: int
    week_index: int | None
    status: str
    kind: str
    resource_slug: str | None
    gate_skill: str | None
    item_type: str
    score_breakdown: dict
    explanation_metadata: dict

    @property
    def key(self) -> str:
        if self.gate_skill:
            return f"gate:{self.gate_skill}"
        return f"resource:{self.resource_slug}"

    @property
    def completed(self) -> bool:
        return self.status == PathItemStatus.COMPLETED.value


@dataclass(frozen=True)
class V2Item:
    """A row to persist on the adapted path."""

    position: int
    week_index: int | None
    status: str
    kind: str
    executable: bool
    resource_slug: str | None
    gate: dict | None
    item_type: str
    score_breakdown: dict
    explanation_metadata: dict


@dataclass(frozen=True)
class AdaptationResult:
    items: tuple[V2Item, ...]
    diff: PathDiff
    changed_skills: tuple[str, ...]
    no_adaptation: bool
    total_estimated_hours: float
    quality: dict | None


@dataclass(frozen=True)
class PathMaterialState:
    key: str
    kind: str
    status: str
    executable: bool
    week_index: int | None
    position: int
    target_skill: str
    intervention: str
    eligibility: str
    prereq_states: tuple[tuple[str, str], ...]


def _prereq_states(meta: dict) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (str(item.get("skill", "")), str(item.get("state", "")))
            for item in meta.get("prerequisites") or []
        )
    )


def _material_from_snapshot(snapshot: PathItemSnapshot) -> PathMaterialState:
    meta = snapshot.explanation_metadata or {}
    return PathMaterialState(
        key=snapshot.key,
        kind=snapshot.kind,
        status=snapshot.status,
        executable=bool(meta.get("executable")),
        week_index=snapshot.week_index,
        position=snapshot.position,
        target_skill=str(meta.get("target_skill") or snapshot.gate_skill or ""),
        intervention=str(meta.get("intervention") or ""),
        eligibility=str(meta.get("eligibility") or ""),
        prereq_states=_prereq_states(meta),
    )


def _material_from_v2(item: V2Item) -> PathMaterialState:
    meta = item.explanation_metadata or {}
    gate_skill = (item.gate or {}).get("skill") if item.gate else None
    key = f"gate:{gate_skill}" if gate_skill else f"resource:{item.resource_slug}"
    return PathMaterialState(
        key=key,
        kind=item.kind,
        status=item.status,
        executable=item.executable,
        week_index=item.week_index,
        position=item.position,
        target_skill=str(meta.get("target_skill") or gate_skill or ""),
        intervention=str(meta.get("intervention") or ""),
        eligibility=str(meta.get("eligibility") or ""),
        prereq_states=_prereq_states(meta),
    )


def _material_signature(
    snapshots: list[PathItemSnapshot],
) -> tuple[PathMaterialState, ...]:
    return tuple(
        sorted(
            (_material_from_snapshot(item) for item in snapshots),
            key=lambda row: (row.position, row.key),
        )
    )


def _material_signature_v2(items: list[V2Item]) -> tuple[PathMaterialState, ...]:
    return tuple(
        sorted(
            (_material_from_v2(item) for item in items),
            key=lambda row: (row.position, row.key),
        )
    )


def _move_reason(
    snapshot: PathItemSnapshot,
    v2_item: V2Item,
    *,
    added: list[DiffEntry],
    new_profile: GapProfile,
    week_offset: int,
) -> str:
    was_executable = bool(snapshot.explanation_metadata.get("executable"))
    if not v2_item.executable:
        return "Waiting: prerequisite evidence or remediation is still required."
    if not was_executable:
        skill = snapshot.gate_skill or snapshot.explanation_metadata.get("target_skill") or ""
        target = _target(new_profile, skill)
        proficiency = _proficiency(new_profile, skill)
        if target is not None and proficiency is not None:
            return (
                f"Moved to Week {v2_item.week_index} because prerequisite "
                f"{skill.replace('_', ' ')} evidence reached {proficiency:.2f} "
                f"(role target {target:.2f}), making this item executable."
            )
        return "New evidence satisfied its prerequisites; the item is now executable."
    if snapshot.week_index == v2_item.week_index:
        return "Still justified; unchanged."

    inserted_before = [
        entry
        for entry in added
        if entry.to_week is not None
        and v2_item.week_index is not None
        and entry.to_week <= v2_item.week_index
    ]
    if inserted_before:
        blocker = inserted_before[0]
        return (
            f"Moved from Week {snapshot.week_index} to Week {v2_item.week_index} "
            f"because {blocker.title} was inserted for {blocker.skill.replace('_', ' ')}."
        )
    if week_offset > 0:
        return (
            f"Moved from Week {snapshot.week_index} to Week {v2_item.week_index} "
            f"because completed work through Week {week_offset} shifted the remaining schedule."
        )
    return "Re-sequenced after path changes."


def _planned_key(item: PlannedItem) -> str:
    if item.gate is not None:
        return f"gate:{item.gate.skill_slug}"
    assert item.candidate is not None
    return f"resource:{item.candidate.resource.slug}"


def _attainment_label(profile: GapProfile, skill: str) -> str:
    for item in profile.items:
        if item.ranked.gap.skill_slug == skill:
            return item.ranked.gap.attainment.value
    return AttainmentStatus.UNKNOWN.value


def _proficiency(profile: GapProfile, skill: str) -> float | None:
    for item in profile.items:
        if item.ranked.gap.skill_slug == skill:
            return item.ranked.gap.proficiency
    return None


def _target(profile: GapProfile, skill: str) -> float | None:
    for item in profile.items:
        if item.ranked.gap.skill_slug == skill:
            return item.ranked.gap.target_level
    return None


def _changed_skills(previous: GapProfile, new: GapProfile) -> tuple[str, ...]:
    def state(profile: GapProfile) -> dict[str, tuple]:
        return {
            item.ranked.gap.skill_slug: (
                item.ranked.gap.evidence_state.value,
                item.ranked.gap.attainment.value,
                # Rounded: recency weights make the last float bits time-dependent.
                (
                    round(item.ranked.gap.proficiency, 6)
                    if item.ranked.gap.proficiency is not None
                    else None
                ),
            )
            for item in profile.items
        }

    before = state(previous)
    after = state(new)
    changed = [
        slug for slug in sorted(set(before) | set(after)) if before.get(slug) != after.get(slug)
    ]
    return tuple(changed)


def _removal_reason(
    snapshot: PathItemSnapshot,
    previous: GapProfile,
    new: GapProfile,
) -> str:
    skill = snapshot.gate_skill or ""
    title = snapshot.explanation_metadata.get("title") or snapshot.resource_slug or ""
    if snapshot.gate_skill:
        proficiency = _proficiency(new, skill)
        target = _target(new, skill)
        if proficiency is not None and target is not None and proficiency + 1e-9 >= target:
            return (
                f"Verification gate for {skill.replace('_', ' ')} resolved: fused proficiency "
                f"{proficiency:.2f} met the role target {target:.2f}."
            )
        return f"Verification gate for {skill.replace('_', ' ')} is no longer required."
    skill = snapshot.explanation_metadata.get("target_skill") or ""
    attainment = _attainment_label(new, skill)
    proficiency = _proficiency(new, skill)
    target = _target(new, skill)
    if attainment == AttainmentStatus.TARGET_MET.value:
        return (
            f"New evidence moved {skill.replace('_', ' ')} to target attainment "
            f"({proficiency:.2f} >= role target {target:.2f}), so remaining "
            f"{skill.replace('_', ' ')} work is no longer justified."
        )
    return (
        f"{title} is no longer justified for {skill.replace('_', ' ')} "
        f"under the updated gap profile."
    )


def _addition_reason(
    item: PlannedItem,
    previous: GapProfile,
    new: GapProfile,
) -> str:
    if item.gate is not None:
        skill = item.gate.skill_slug
        return (
            f"{skill.replace('_', ' ')} is UNKNOWN and role-relevant for "
            f"{new.role_name}; verification is required before downstream learning."
        )
    assert item.candidate is not None
    skill = item.candidate.primary_skill
    before = _attainment_label(previous, skill)
    after = _attainment_label(new, skill)
    if before != after:
        return (
            f"Evidence moved {skill.replace('_', ' ')} from {before} to {after}, "
            f"creating a diagnosed gap; {item.candidate.resource.title} was inserted."
        )
    return (
        f"{item.candidate.resource.title} covers {skill.replace('_', ' ')}, "
        f"a diagnosed gap for {new.role_name}."
    )


def _to_v2(item: PlannedItem) -> V2Item:
    if item.gate is not None:
        return V2Item(
            position=item.position,
            week_index=item.week_index,
            status=PathItemStatus.PENDING.value,
            kind=PathItemKind.VERIFICATION_GATE.value,
            executable=True,
            resource_slug=None,
            gate=item.gate.as_dict(),
            item_type=PathItemType.VERIFICATION_GATE.value,
            score_breakdown={},
            explanation_metadata={
                "resource_slug": "",
                "title": f"Verify {item.gate.skill_slug.replace('_', ' ')}",
                "target_skill": item.gate.skill_slug,
                "intervention": "VERIFY",
                "eligibility": "GATE",
                "prerequisites": [],
                "explanation": item.gate.reason,
                "url": None,
                "url_status": None,
                "duration_hours": 0,
                "type": PathItemType.VERIFICATION_GATE.value,
                "kind": PathItemKind.VERIFICATION_GATE.value,
                "executable": True,
                "gate": item.gate.as_dict(),
                "causality": item.cause.as_dict() if item.cause else {},
            },
        )
    assert item.candidate is not None
    candidate = item.candidate
    item_type = (
        PathItemType.ASSESSMENT.value
        if candidate.resource.type == ResourceType.ASSESSMENT.value
        else PathItemType.RESOURCE.value
    )
    status = PathItemStatus.PENDING.value
    if item.kind == PathItemKind.WAITING_FOR_VERIFICATION.value:
        status = PathItemStatus.WAITING_FOR_VERIFICATION.value
    elif item.kind == PathItemKind.WAITING_FOR_REMEDIATION.value:
        status = PathItemStatus.WAITING_FOR_REMEDIATION.value
    return V2Item(
        position=item.position,
        week_index=item.week_index,
        status=status,
        kind=item.kind,
        executable=item.executable,
        resource_slug=candidate.resource.slug,
        gate=None,
        item_type=item_type,
        score_breakdown=candidate.breakdown.as_dict(),
        explanation_metadata={
            "resource_slug": candidate.resource.slug,
            "title": candidate.resource.title,
            "target_skill": candidate.primary_skill,
            "intervention": candidate.intervention.value,
            "eligibility": candidate.eligibility.status.value,
            "prerequisites": [
                {
                    "skill": check.skill_slug,
                    "min_level": check.min_level,
                    "state": check.state.value,
                    "observed": check.observed,
                }
                for check in candidate.eligibility.checks
            ],
            "explanation": candidate.explanation,
            "url": candidate.resource.url,
            "url_status": candidate.resource.url_status,
            "duration_hours": candidate.resource.duration_hours,
            "type": candidate.resource.type,
            "kind": item.kind,
            "executable": item.executable,
            "gate": None,
            "causality": item.cause.as_dict() if item.cause else {},
        },
    )


def _freeze(snapshot: PathItemSnapshot) -> V2Item:
    meta = dict(snapshot.explanation_metadata or {})
    meta["executable"] = False  # completed work is not executable anymore
    return V2Item(
        position=snapshot.position,
        week_index=snapshot.week_index,
        status=PathItemStatus.COMPLETED.value,
        kind=snapshot.kind,
        executable=False,
        resource_slug=snapshot.resource_slug,
        gate=(meta.get("gate") or None),
        item_type=snapshot.item_type,
        score_breakdown=dict(snapshot.score_breakdown or {}),
        explanation_metadata=meta,
    )


def _assign_positions(completed: list[V2Item], remaining: list[V2Item]) -> list[V2Item]:
    """Completed items keep historical positions; remaining items receive the
    lowest free positions in planned order. No collisions, ordering preserved."""
    taken = {item.position for item in completed}
    cursor = 0
    reassigned: list[V2Item] = []
    for item in remaining:
        while cursor in taken:
            cursor += 1
        taken.add(cursor)
        reassigned.append(
            V2Item(
                position=cursor,
                week_index=item.week_index,
                status=item.status,
                kind=item.kind,
                executable=item.executable,
                resource_slug=item.resource_slug,
                gate=item.gate,
                item_type=item.item_type,
                score_breakdown=item.score_breakdown,
                explanation_metadata=item.explanation_metadata,
            )
        )
        cursor += 1
    return reassigned


def adapt_path(
    *,
    previous_items: list[PathItemSnapshot],
    previous_profile: GapProfile,
    new_profile: GapProfile,
    catalog: list[ResourceSpec],
    edges: list[SkillEdge],
    prefs: LearnerPreferences,
) -> AdaptationResult:
    completed_snapshots = [item for item in previous_items if item.completed]
    remaining_snapshots = [item for item in previous_items if not item.completed]
    frozen = [_freeze(item) for item in sorted(completed_snapshots, key=lambda i: i.position)]

    planned = generate_path(new_profile, catalog, edges, prefs)
    new_by_key = {_planned_key(item): item for item in planned.items}
    remaining_by_key = {item.key: item for item in remaining_snapshots}

    changed = _changed_skills(previous_profile, new_profile)

    completed_keys = {item.key for item in completed_snapshots}
    kept_keys = [key for key in new_by_key if key in remaining_by_key]
    # A resource already completed is never re-added as pending work.
    added_keys = [
        key
        for key in new_by_key
        if key not in remaining_by_key and key not in completed_keys
    ]
    removed_keys = [key for key in remaining_by_key if key not in new_by_key]

    # Re-plan remaining work in generated order, weeks shifted past completed work.
    completed_weeks = [item.week_index or 0 for item in frozen]
    week_offset = max(completed_weeks, default=0)
    remaining_planned: list[PlannedItem] = []
    for item in planned.items:
        key = _planned_key(item)
        if key in completed_keys:
            continue
        if key not in kept_keys and key not in added_keys:
            continue
        shifted = item
        if item.week_index is not None:
            shifted = PlannedItem(
                candidate=item.candidate,
                position=item.position,
                week_index=item.week_index + week_offset,
                cause=item.cause,
                kind=item.kind,
                executable=item.executable,
                gate=item.gate,
            )
        remaining_planned.append(shifted)

    remaining_v2 = [_to_v2(item) for item in remaining_planned]
    remaining_v2 = _assign_positions(frozen, remaining_v2)
    items = tuple(sorted([*frozen, *remaining_v2], key=lambda i: i.position))

    # Material no-op: evidence may change without learner-visible path mutation.
    if _material_signature(previous_items) == _material_signature_v2(list(items)):
        return AdaptationResult(
            items=items,
            diff=PathDiff(changed_skills=changed),
            changed_skills=changed,
            no_adaptation=True,
            total_estimated_hours=0.0,
            quality=None,
        )

    # Diff with deterministic reasons.
    added: list[DiffEntry] = []
    removed: list[DiffEntry] = []
    moved: list[DiffEntry] = []
    unchanged: list[DiffEntry] = []
    blocked: list[DiffEntry] = []

    for key in added_keys:
        item = new_by_key[key]
        skill = item.gate.skill_slug if item.gate else item.candidate.primary_skill
        title = (
            f"Verify {skill.replace('_', ' ')}"
            if item.gate
            else item.candidate.resource.title
        )
        planned_week = item.week_index + week_offset if item.week_index is not None else None
        added.append(
            DiffEntry(
                key=key,
                skill=skill,
                title=title,
                reason=_addition_reason(item, previous_profile, new_profile),
                to_week=planned_week,
            )
        )
    for key in removed_keys:
        snapshot = remaining_by_key[key]
        removed.append(
            DiffEntry(
                key=key,
                skill=snapshot.gate_skill
                or snapshot.explanation_metadata.get("target_skill")
                or "",
                title=snapshot.explanation_metadata.get("title") or key,
                reason=_removal_reason(snapshot, previous_profile, new_profile),
            )
        )
    for key in kept_keys:
        snapshot = remaining_by_key[key]
        v2_item = next(item for item in remaining_v2 if _v2_key(item) == key)
        skill = snapshot.gate_skill or snapshot.explanation_metadata.get("target_skill") or ""
        title = snapshot.explanation_metadata.get("title") or key
        reason = _move_reason(
            snapshot,
            v2_item,
            added=added,
            new_profile=new_profile,
            week_offset=week_offset,
        )
        if not v2_item.executable:
            blocked.append(
                DiffEntry(
                    key=key,
                    skill=skill,
                    title=title,
                    reason=reason,
                    from_week=snapshot.week_index,
                    to_week=v2_item.week_index,
                )
            )
        elif (
            snapshot.week_index != v2_item.week_index
            or bool(snapshot.explanation_metadata.get("executable")) != v2_item.executable
        ):
            moved.append(
                DiffEntry(
                    key=key,
                    skill=skill,
                    title=title,
                    reason=reason,
                    from_week=snapshot.week_index,
                    to_week=v2_item.week_index,
                )
            )
        else:
            unchanged.append(
                DiffEntry(key=key, skill=skill, title=title, reason=reason)
            )

    hours = round(
        sum(
            item.explanation_metadata.get("duration_hours") or 0
            for item in remaining_v2
            if item.executable and item.resource_slug
        ),
        4,
    )
    diff = PathDiff(
        added=tuple(added),
        removed=tuple(removed),
        moved=tuple(moved),
        unchanged=tuple(unchanged),
        blocked=tuple(blocked),
        changed_skills=changed,
    )
    return AdaptationResult(
        items=items,
        diff=diff,
        changed_skills=changed,
        no_adaptation=False,
        total_estimated_hours=hours,
        quality=planned.quality,
    )


def _v2_key(item: V2Item) -> str:
    if item.gate:
        return f"gate:{item.gate['skill']}"
    return f"resource:{item.resource_slug}"
