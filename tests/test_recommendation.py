from app.core.enums import EligibilityStatus, PrerequisiteEvidenceState
from app.ontology.load import ResourcePrereqSpec, ResourceSkillSpec, ResourceSpec, load_ontology
from app.services.recommendation.config import load_recommendation_config
from app.services.recommendation.eligibility import evaluate_resource
from app.services.recommendation.models import LearnerPreferences
from app.services.recommendation.scorer import difficulty_fit, duration_fit, score_resource
from app.services.sequencing.weekly_packer import pack_weeks
from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet
from app.services.skill_graph.dependency import SkillEdge
from app.core.enums import RequiredStatus
from app.core.skill_state import resolve_skill_status
from app.services.gap_engine.profile import build_gap_profile
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.path.generator import generate_path
from app.services.sequencing.topological import sequence_resources
from app.services.recommendation.scorer import score_candidates


def _fused(slug: str, proficiency: float | None) -> FusedSkill:
    return FusedSkill(
        skill_slug=slug,
        proficiency=proficiency,
        confidence=None if proficiency is None else 0.8,
        status=resolve_skill_status(
            has_evidence=proficiency is not None,
            proficiency=proficiency,
            target_level=0.8,
        ),
        evidence_count=0 if proficiency is None else 1,
        conflict=False,
        conflict_spread=0.0,
        dominant_source=None if proficiency is None else "ASSESSMENT",
        weights=(),
        reason="fixture",
    )


def _resource(slug: str, skill: str, *, coverage: float, duration: float = 4, difficulty: int = 2, modes=None, prereqs=None, rtype="course"):
    return ResourceSpec(
        slug=slug,
        title=slug,
        description=slug,
        type=rtype,
        difficulty=difficulty,
        duration_hours=duration,
        source="test",
        url=None,
        url_status="unavailable",
        learning_modes=list(modes or ["reading"]),
        is_active=True,
        skills=[ResourceSkillSpec(skill, coverage, 0.2, True)],
        prerequisites=[ResourcePrereqSpec(p[0], p[1]) for p in (prereqs or [])],
    )


def test_catalog_has_slice2_volume_and_valid_urls():
    bundle = load_ontology()
    assert 50 <= len(bundle.resources) <= 75
    slugs = [item.slug for item in bundle.resources]
    assert len(slugs) == len(set(slugs))
    for item in bundle.resources:
        if item.url_status == "verified":
            assert item.url and item.url.startswith("https://")
        if item.url_status == "unavailable":
            assert item.url is None


def test_unknown_prerequisite_is_not_unsatisfied():
    resource = _resource("dl", "neural_networks", coverage=0.8, prereqs=[("python", 0.5)])
    unknown = evaluate_resource(resource, {"python": None})
    missing = evaluate_resource(resource, {"python": 0.2})
    ok = evaluate_resource(resource, {"python": 0.7})
    assert unknown.checks[0].state is PrerequisiteEvidenceState.UNKNOWN
    assert unknown.status is EligibilityStatus.BLOCKED_BY_UNKNOWN
    assert missing.checks[0].state is PrerequisiteEvidenceState.UNSATISFIED
    assert missing.status is EligibilityStatus.BLOCKED_BY_KNOWN_GAP
    assert ok.status is EligibilityStatus.ELIGIBLE


def test_stronger_coverage_outranks_mention():
    role = RoleCompetencySet(
        "r",
        "R",
        (RoleCompetency("statistics", "Statistics", 0.8, 0.9, RequiredStatus.CORE),),
    )
    fused = {"statistics": _fused("statistics", 0.35)}
    profile = build_gap_profile(fused_by_slug=fused, role=role, edges=[])
    prefs = LearnerPreferences(8, "READING")
    strong = score_resource(_resource("a", "statistics", coverage=0.90), profile, prefs)
    weak = score_resource(_resource("b", "statistics", coverage=0.30), profile, prefs)
    assert strong.breakdown.skill_gap_fit > weak.breakdown.skill_gap_fit
    assert strong.breakdown.final_score > weak.breakdown.final_score


def test_same_resource_scores_differ_by_role():
    stats = RoleCompetency("statistics", "Statistics", 0.8, 0.9, RequiredStatus.CORE)
    owasp = RoleCompetency("owasp_top10", "OWASP", 0.8, 0.9, RequiredStatus.CORE)
    resource = _resource("stats-course", "statistics", coverage=0.85)
    aiml = build_gap_profile(
        fused_by_slug={"statistics": _fused("statistics", 0.3)},
        role=RoleCompetencySet("aiml", "AI/ML", (stats,)),
        edges=[],
    )
    cyber = build_gap_profile(
        fused_by_slug={"statistics": _fused("statistics", 0.3)},
        role=RoleCompetencySet("cyber", "Cyber", (owasp,)),
        edges=[],
    )
    prefs = LearnerPreferences(8, "READING")
    left = score_resource(resource, aiml, prefs)
    right = score_resource(resource, cyber, prefs)
    assert left.breakdown.role_importance > right.breakdown.role_importance
    assert left.breakdown.final_score > right.breakdown.final_score


def test_hands_on_style_boosts_labs():
    role = RoleCompetencySet(
        "r", "R", (RoleCompetency("python", "Python", 0.8, 0.9, RequiredStatus.CORE),)
    )
    fused = {"python": _fused("python", 0.4)}
    profile = build_gap_profile(fused_by_slug=fused, role=role, edges=[])
    lab = _resource("lab", "python", coverage=0.8, modes=["lab", "project"], rtype="lab")
    reading = _resource("read", "python", coverage=0.8, modes=["reading"])
    hands = LearnerPreferences(8, "HANDS_ON")
    video = LearnerPreferences(8, "READING")
    assert score_resource(lab, profile, hands).breakdown.learning_style_fit > score_resource(
        reading, profile, hands
    ).breakdown.learning_style_fit
    assert score_resource(reading, profile, video).breakdown.learning_style_fit > score_resource(
        lab, profile, video
    ).breakdown.learning_style_fit


def test_duration_fit_and_weekly_packing_change_with_budget():
    assert duration_fit(4, 15) > duration_fit(4, 5) or duration_fit(30, 15) > duration_fit(30, 5)
    short = _resource("a", "python", coverage=0.8, duration=3)
    long = _resource("b", "python", coverage=0.8, duration=4)
    role = RoleCompetencySet(
        "r", "R", (RoleCompetency("python", "Python", 0.8, 0.9, RequiredStatus.CORE),)
    )
    profile = build_gap_profile(
        fused_by_slug={"python": _fused("python", 0.4)}, role=role, edges=[]
    )
    prefs = LearnerPreferences(8, "MIXED")
    scored = score_candidates([short, long], profile, prefs)
    five = pack_weeks(scored, 5)
    fifteen = pack_weeks(scored, 15)
    assert five[0].week_index != five[1].week_index
    assert fifteen[0].week_index == fifteen[1].week_index


def test_difficulty_fit_penalizes_mismatch():
    assert difficulty_fit(5, 0.2) < difficulty_fit(2, 0.2)
    assert difficulty_fit(1, 0.9) < difficulty_fit(4, 0.9)


def test_high_score_can_appear_later_than_blocker():
    python = _resource("python-course", "python", coverage=0.9, difficulty=2)
    ml = _resource(
        "ml-course",
        "ml_fundamentals",
        coverage=0.9,
        difficulty=3,
        prereqs=[("python", 0.7)],
    )
    role = RoleCompetencySet(
        "r",
        "R",
        (
            RoleCompetency("python", "Python", 0.85, 0.95, RequiredStatus.CORE),
            RoleCompetency("ml_fundamentals", "ML", 0.85, 0.95, RequiredStatus.CORE),
        ),
    )
    edges = [SkillEdge("python", "ml_fundamentals", "HARD_PREREQUISITE", 0.95)]
    profile = build_gap_profile(
        fused_by_slug={"python": _fused("python", 0.45), "ml_fundamentals": _fused("ml_fundamentals", 0.3)},
        role=role,
        edges=edges,
    )
    prefs = LearnerPreferences(10, "READING")
    scored = score_candidates([python, ml], profile, prefs)
    by_score = [item.resource.slug for item in scored]
    ordered = [item.resource.slug for item in sequence_resources(scored, edges)]
    assert "python-course" in ordered
    assert ordered.index("python-course") < ordered.index("ml-course")
    if by_score[0] == "ml-course":
        assert ordered[0] != "ml-course" or ordered.index("python-course") == 0


def test_weights_are_normalized_hypothesis():
    cfg = load_recommendation_config()
    assert abs(cfg.weight_total() - 1.0) < 1e-9


def test_generate_path_uses_only_catalog_resources():
    bundle = load_ontology()
    catalog_slugs = {item.slug for item in bundle.resources}
    role = next(item for item in bundle.roles if item.slug == "ai-ml-engineer")
    from app.services.skill_graph.competency import RoleCompetency as RC

    competencies = tuple(
        RC(s.slug, s.slug, s.target_level, s.importance, RequiredStatus(s.required_status))
        for s in role.skills
    )
    fused = {
        "python": _fused("python", 0.45),
        "statistics": _fused("statistics", 0.90),
        "ml_fundamentals": _fused("ml_fundamentals", 0.30),
    }
    edges = [
        SkillEdge(rel.source, rel.target, rel.type, rel.strength) for rel in bundle.relationships
    ]
    profile = build_gap_profile(
        fused_by_slug=fused,
        role=RoleCompetencySet(role.slug, role.name, competencies),
        edges=edges,
    )
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(5, "HANDS_ON"))
    assert path.items
    for item in path.items:
        assert item.candidate.resource.slug in catalog_slugs
    assert generate_path(
        profile, bundle.resources, edges, LearnerPreferences(5, "HANDS_ON")
    ).items == path.items


def test_blocker_chain_unblocks_then_assigns_target():
    linux = _resource("linux-course", "linux_fundamentals", coverage=0.9)
    python = _resource("python-course", "python", coverage=0.9, prereqs=[("linux_fundamentals", 0.6)])
    ml = _resource("ml-course", "ml_fundamentals", coverage=0.9, prereqs=[("python", 0.7)])
    role = RoleCompetencySet(
        "r",
        "R",
        (
            RoleCompetency("linux_fundamentals", "Linux", 0.8, 0.9, RequiredStatus.CORE),
            RoleCompetency("python", "Python", 0.85, 0.95, RequiredStatus.CORE),
            RoleCompetency("ml_fundamentals", "ML", 0.85, 0.95, RequiredStatus.CORE),
        ),
    )
    edges = [
        SkillEdge("linux_fundamentals", "python", "HARD_PREREQUISITE", 0.95),
        SkillEdge("python", "ml_fundamentals", "HARD_PREREQUISITE", 0.95),
    ]
    profile = build_gap_profile(
        fused_by_slug={
            "linux_fundamentals": _fused("linux_fundamentals", 0.20),
            "python": _fused("python", 0.30),
            "ml_fundamentals": _fused("ml_fundamentals", 0.20),
        },
        role=role,
        edges=edges,
    )
    path = generate_path(
        profile, [linux, python, ml], edges, LearnerPreferences(10, "READING")
    )
    slugs = [item.candidate.resource.slug for item in path.items]
    assert slugs.index("linux-course") < slugs.index("python-course")
    assert slugs.index("python-course") < slugs.index("ml-course")


def test_unknown_catalog_prereq_is_not_mastered():
    bundle = load_ontology()
    resource = next(item for item in bundle.resources if item.slug == "docker-compose-guide")
    unknown = evaluate_resource(resource, {"docker": None})
    assert unknown.status is EligibilityStatus.BLOCKED_BY_UNKNOWN
    assert unknown.checks[0].state is PrerequisiteEvidenceState.UNKNOWN


def test_personas_d_and_e_generate_different_paths():
    bundle = load_ontology()
    role = next(item for item in bundle.roles if item.slug == "ai-ml-engineer")
    from app.services.skill_graph.competency import RoleCompetency as RC

    competencies = tuple(
        RC(s.slug, s.slug, s.target_level, s.importance, RequiredStatus(s.required_status))
        for s in role.skills
    )
    edges = [
        SkillEdge(rel.source, rel.target, rel.type, rel.strength) for rel in bundle.relationships
    ]
    role_set = RoleCompetencySet(role.slug, role.name, competencies)
    strong = build_gap_profile(
        fused_by_slug={
            "python": _fused("python", 0.90),
            "sql": _fused("sql", 0.80),
            "statistics": _fused("statistics", 0.88),
            "ml_fundamentals": _fused("ml_fundamentals", 0.82),
        },
        role=role_set,
        edges=edges,
    )
    limited = build_gap_profile(
        fused_by_slug={
            "python": _fused("python", 0.40),
            "statistics": _fused("statistics", 0.30),
            "ml_fundamentals": _fused("ml_fundamentals", 0.20),
        },
        role=role_set,
        edges=edges,
    )
    path_d = generate_path(strong, bundle.resources, edges, LearnerPreferences(15, "READING"))
    path_e = generate_path(limited, bundle.resources, edges, LearnerPreferences(5, "HANDS_ON"))
    slugs_d = [item.candidate.resource.slug for item in path_d.items]
    slugs_e = [item.candidate.resource.slug for item in path_e.items]
    weeks_d = [item.week_index for item in path_d.items]
    weeks_e = [item.week_index for item in path_e.items]
    assert slugs_d
    assert slugs_e
    assert slugs_d != slugs_e or weeks_d != weeks_e
    assert path_d.weekly_hours != path_e.weekly_hours
