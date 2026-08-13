"""Verification gates. Not assessment runtime. UNKNOWN means we need evidence."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import ActionClass, EvidenceState, GateState, PathItemKind, RequiredStatus
from app.services.gap_engine.profile import ExplainedGap, GapProfile
from app.services.skill_graph.dependency import SkillEdge


@dataclass(frozen=True)
class VerificationGate:
    skill_slug: str
    target_role: str
    reason: str
    priority: float
    required_before: tuple[str, ...]
    state: GateState = GateState.PENDING

    def as_dict(self) -> dict:
        return {
            "skill": self.skill_slug,
            "target_role": self.target_role,
            "reason": self.reason,
            "priority": self.priority,
            "required_before": list(self.required_before),
            "state": self.state.value,
        }


def _hard_dependents(skill_slug: str, profile: GapProfile, edges: list[SkillEdge]) -> tuple[str, ...]:
    role_skills = {item.ranked.gap.skill_slug for item in profile.items}
    return tuple(
        sorted(
            edge.target
            for edge in edges
            if edge.source == skill_slug
            and edge.relationship_type == "HARD_PREREQUISITE"
            and edge.target in role_skills
        )
    )


def select_verification_skills(
    profile: GapProfile,
    edges: list[SkillEdge],
    *,
    max_gates: int = 8,
) -> list[ExplainedGap]:
    """UNKNOWN role competencies ranked by verification_priority, not gap_priority."""
    unknown = [
        item
        for item in profile.items
        if item.action is ActionClass.VERIFY
        and item.ranked.gap.evidence_state is EvidenceState.UNKNOWN
        and item.ranked.gap.required_status
        in {RequiredStatus.CORE.value, RequiredStatus.ELECTIVE.value}
    ]
    hard_sources = {
        edge.source
        for edge in edges
        if edge.relationship_type == "HARD_PREREQUISITE"
        and edge.target in {item.ranked.gap.skill_slug for item in unknown}
    }

    def key(item: ExplainedGap) -> tuple:
        slug = item.ranked.gap.skill_slug
        foundation = 0 if slug in hard_sources else 1
        core = 0 if item.ranked.gap.required_status == RequiredStatus.CORE.value else 1
        return (core, foundation, -item.ranked.verification_priority, slug)

    ranked = sorted(unknown, key=key)
    return ranked[:max_gates]


def resolve_gate_state(skill_slug: str, profile: GapProfile) -> GateState:
    """Resolve a gate from the learner's fused state against the ROLE target.

    The role's target_level decides VERIFIED/FAILED. An assessment's
    pass_threshold is about test performance and is never used here.
    """
    for item in profile.items:
        if item.ranked.gap.skill_slug != skill_slug:
            continue
        if item.ranked.gap.evidence_state is EvidenceState.UNKNOWN:
            return GateState.PENDING
        if item.ranked.gap.target_met is True:
            return GateState.VERIFIED
        return GateState.FAILED
    return GateState.PENDING


def build_gates(
    profile: GapProfile,
    edges: list[SkillEdge],
    *,
    max_gates: int = 8,
) -> list[VerificationGate]:
    gates: list[VerificationGate] = []
    for item in select_verification_skills(profile, edges, max_gates=max_gates):
        slug = item.ranked.gap.skill_slug
        dependents = _hard_dependents(slug, profile, edges)
        reason = (
            f"{slug.replace('_', ' ')} is an UNKNOWN "
            f"{item.ranked.gap.required_status.lower()} competency for "
            f"{profile.role_name}, so the system requires evidence before "
            f"recommending downstream learning."
        )
        if dependents:
            reason += (
                f" It is a HARD prerequisite of {', '.join(dependents)}."
            )
        gates.append(
            VerificationGate(
                skill_slug=slug,
                target_role=profile.role_slug,
                reason=reason,
                priority=item.ranked.verification_priority,
                required_before=dependents,
                state=GateState.PENDING,
            )
        )
    return gates
