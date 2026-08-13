from app.core.enums import ActionClass, AttainmentStatus, GapStatus, RequiredStatus
from app.core.skill_state import resolve_skill_status
from app.services.gap_engine.actions import classify_action
from app.services.gap_engine.calculator import calculate_gap
from app.services.gap_engine.profile import build_gap_profile
from app.services.gap_engine.prioritizer import prioritize_gap
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet
from app.services.skill_graph.dependency import (
    DownstreamImpact,
    PrerequisiteGate,
    SkillEdge,
    resolve_prerequisite_gate,
)


def _fused(slug: str, proficiency: float) -> FusedSkill:
    return FusedSkill(
        skill_slug=slug,
        proficiency=proficiency,
        confidence=0.8,
        status=resolve_skill_status(has_evidence=True, proficiency=proficiency, target_level=0.8),
        evidence_count=1,
        conflict=False,
        conflict_spread=0.0,
        dominant_source="ASSESSMENT",
        weights=(),
        reason="fixture",
    )


def _by_slug(profile):
    return {item.ranked.gap.skill_slug: item for item in profile.items}


def test_below_target_near_is_not_target_met():
    competency = RoleCompetency("stats", "Statistics", 0.75, 0.85, RequiredStatus.CORE)
    gap = calculate_gap(_fused("stats", 0.65), competency)
    assert gap.target_met is False
    assert gap.attainment is AttainmentStatus.NEAR_TARGET
    assert gap.gap_status is GapStatus.DEVELOPING
    assert gap.gap_status is not GapStatus.SATISFIED
    assert classify_action(gap, PrerequisiteGate("stats", False, (), False, ())) is ActionClass.REINFORCE


def test_unknown_is_verify_not_numeric_gap():
    competency = RoleCompetency("mlops", "MLOps", 0.65, 0.8, RequiredStatus.CORE)
    gap = calculate_gap(None, competency)
    ranked = prioritize_gap(gap, DownstreamImpact("mlops", (), (), (), (), False))
    assert gap.proficiency is None
    assert gap.gap is None
    assert gap.attainment is AttainmentStatus.UNKNOWN
    assert gap.target_met is None
    assert ranked.gap_priority == 0.0
    assert ranked.verification_priority > 0
    assert ranked.priority == ranked.gap_priority
    gate = PrerequisiteGate("mlops", False, (), False, ())
    assert classify_action(gap, gate) is ActionClass.VERIFY


def test_known_material_gap_is_remediate():
    competency = RoleCompetency("stats", "Statistics", 0.80, 0.90, RequiredStatus.CORE)
    gap = calculate_gap(_fused("stats", 0.35), competency)
    assert gap.attainment is AttainmentStatus.GAP
    assert classify_action(gap, PrerequisiteGate("stats", False, (), False, ())) is ActionClass.REMEDIATE


def test_target_met_is_advance():
    competency = RoleCompetency("python", "Python", 0.75, 0.95, RequiredStatus.CORE)
    gap = calculate_gap(_fused("python", 0.80), competency)
    assert gap.target_met is True
    assert gap.attainment is AttainmentStatus.TARGET_MET
    assert gap.gap_status is GapStatus.SATISFIED
    assert classify_action(gap, PrerequisiteGate("python", False, (), False, ())) is ActionClass.ADVANCE


def test_hard_prerequisite_blocks_downstream():
    role = RoleCompetencySet(
        "demo",
        "Demo",
        (
            RoleCompetency("stats", "Statistics", 0.80, 0.90, RequiredStatus.CORE),
            RoleCompetency("ml", "ML", 0.85, 0.95, RequiredStatus.CORE),
        ),
    )
    edges = [SkillEdge("stats", "ml", "HARD_PREREQUISITE", 0.9)]
    fused = {"stats": _fused("stats", 0.35), "ml": _fused("ml", 0.55)}
    by = _by_slug(build_gap_profile(fused_by_slug=fused, role=role, edges=edges))
    assert by["ml"].gate.blocked is True
    assert by["ml"].gate.blockers == ("stats",)
    assert by["ml"].action is ActionClass.REMEDIATE_BLOCKER
    assert by["stats"].action is ActionClass.REMEDIATE
    assert by["stats"].gate.blocked is False


def test_soft_prerequisite_does_not_hard_block():
    role = RoleCompetencySet(
        "demo",
        "Demo",
        (
            RoleCompetency("stats", "Statistics", 0.80, 0.90, RequiredStatus.CORE),
            RoleCompetency("ml", "ML", 0.85, 0.95, RequiredStatus.CORE),
        ),
    )
    edges = [SkillEdge("stats", "ml", "SOFT_PREREQUISITE", 0.7)]
    fused = {"stats": _fused("stats", 0.35), "ml": _fused("ml", 0.55)}
    by = _by_slug(build_gap_profile(fused_by_slug=fused, role=role, edges=edges))
    assert by["ml"].gate.blocked is False
    assert by["ml"].gate.preparation_needed is True
    assert by["ml"].gate.preparation_skills == ("stats",)
    assert by["ml"].action is ActionClass.REMEDIATE


def test_related_does_not_block_or_prepare():
    gate = resolve_prerequisite_gate(
        skill_slug="ml",
        edges=[SkillEdge("stats", "ml", "RELATED", 0.5)],
        prereq_met={"stats": False},
    )
    assert gate.blocked is False
    assert gate.blockers == ()
    assert gate.preparation_needed is False
    assert gate.preparation_skills == ()


def test_gap_priority_and_action_priority_are_distinct():
    role = RoleCompetencySet(
        "demo",
        "Demo",
        (
            RoleCompetency("stats", "Statistics", 0.80, 0.90, RequiredStatus.CORE),
            RoleCompetency("ml", "ML", 0.85, 0.95, RequiredStatus.CORE),
        ),
    )
    edges = [SkillEdge("stats", "ml", "HARD_PREREQUISITE", 0.9)]
    fused = {"stats": _fused("stats", 0.35), "ml": _fused("ml", 0.20)}
    by = _by_slug(build_gap_profile(fused_by_slug=fused, role=role, edges=edges))
    assert by["ml"].ranked.gap.gap > by["stats"].ranked.gap.gap
    assert by["stats"].action_priority > by["ml"].action_priority
    assert by["ml"].ranked.gap_priority != by["ml"].action_priority
    assert by["ml"].action is ActionClass.REMEDIATE_BLOCKER
    assert by["stats"].action is ActionClass.REMEDIATE
