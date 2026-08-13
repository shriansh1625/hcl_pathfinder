from app.core.enums import GapStatus, RequiredStatus
from app.core.skill_state import resolve_skill_status
from app.services.gap_engine.calculator import calculate_gap
from app.services.gap_engine.profile import build_gap_profile
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet
from app.services.skill_graph.dependency import DownstreamImpact, SkillEdge, downstream_impact
from app.services.gap_engine.prioritizer import prioritize_gap


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


def test_satisfied_priority_is_zero():
    competency = RoleCompetency("python", "Python", 0.85, 0.95, RequiredStatus.CORE)
    gap = calculate_gap(_fused("python", 0.90), competency)
    ranked = prioritize_gap(
        gap,
        DownstreamImpact("python", ("ml",), (), ("ml",), (), True),
    )
    assert gap.gap_status is GapStatus.SATISFIED
    assert ranked.priority == 0.0
    assert ranked.is_blocking is False


def test_unknown_gap_is_not_zero():
    competency = RoleCompetency("mlops", "MLOps", 0.65, 0.8, RequiredStatus.CORE)
    gap = calculate_gap(None, competency)
    assert gap.gap_status is GapStatus.UNKNOWN
    assert gap.proficiency is None
    assert gap.gap is None


def test_related_edges_do_not_create_descendants():
    edges = [SkillEdge("a", "b", "RELATED", 0.5)]
    impact = downstream_impact(skill_slug="a", edges=edges, role_slugs={"a", "b"})
    assert impact.hard_descendants == ()
    assert impact.soft_descendants == ()
    assert impact.is_blocking is False


def test_hard_prerequisite_is_blocking_soft_is_not():
    edges = [
        SkillEdge("python", "ml", "HARD_PREREQUISITE", 0.9),
        SkillEdge("stats", "ml", "SOFT_PREREQUISITE", 0.7),
    ]
    role = {"python", "stats", "ml"}
    hard = downstream_impact(skill_slug="python", edges=edges, role_slugs=role)
    soft = downstream_impact(skill_slug="stats", edges=edges, role_slugs=role)
    assert hard.is_blocking is True
    assert "ml" in hard.hard_role_descendants
    assert soft.is_blocking is False
    assert "ml" in soft.soft_role_descendants


def test_downstream_impact_can_outrank_a_larger_raw_gap():
    edges = [
        SkillEdge("blocker", "d1", "HARD_PREREQUISITE", 1.0),
        SkillEdge("blocker", "d2", "HARD_PREREQUISITE", 1.0),
        SkillEdge("blocker", "d3", "HARD_PREREQUISITE", 1.0),
    ]
    role = RoleCompetencySet(
        role_slug="demo",
        role_name="Demo",
        competencies=(
            RoleCompetency("blocker", "Blocker", 0.80, 0.90, RequiredStatus.CORE),
            RoleCompetency("leaf", "Leaf", 0.80, 0.90, RequiredStatus.CORE),
            RoleCompetency("d1", "D1", 0.80, 0.90, RequiredStatus.CORE),
            RoleCompetency("d2", "D2", 0.80, 0.90, RequiredStatus.CORE),
            RoleCompetency("d3", "D3", 0.80, 0.90, RequiredStatus.CORE),
        ),
    )
    fused = {
        "blocker": _fused("blocker", 0.50),  # gap 0.30, three HARD descendants
        "leaf": _fused("leaf", 0.35),  # gap 0.45, no downstream
    }
    profile = build_gap_profile(fused_by_slug=fused, role=role, edges=edges)
    by_skill = {item.ranked.gap.skill_slug: item.ranked for item in profile.items}
    assert by_skill["leaf"].gap.gap > by_skill["blocker"].gap.gap
    assert by_skill["blocker"].priority > by_skill["leaf"].priority
    assert by_skill["blocker"].is_blocking is True
    assert by_skill["leaf"].is_blocking is False


def test_hard_descendants_raise_priority_more_than_soft():
    competency = RoleCompetency("x", "X", 0.80, 0.90, RequiredStatus.CORE)
    gap = calculate_gap(_fused("x", 0.40), competency)
    hard = prioritize_gap(
        gap,
        DownstreamImpact("x", ("a",), (), ("a",), (), True),
    )
    soft = prioritize_gap(
        gap,
        DownstreamImpact("x", (), ("a",), (), ("a",), False),
    )
    none = prioritize_gap(
        gap,
        DownstreamImpact("x", (), (), (), (), False),
    )
    assert hard.priority > soft.priority > none.priority
    assert hard.is_blocking is True
    assert soft.is_blocking is False


def test_non_role_skills_are_absent_from_gap_profile():
    role = RoleCompetencySet(
        role_slug="demo",
        role_name="Demo",
        competencies=(RoleCompetency("python", "Python", 0.8, 0.9, RequiredStatus.CORE),),
    )
    fused = {"python": _fused("python", 0.4), "javascript": _fused("javascript", 0.1)}
    profile = build_gap_profile(fused_by_slug=fused, role=role, edges=[])
    slugs = {item.ranked.gap.skill_slug for item in profile.items}
    assert slugs == {"python"}
