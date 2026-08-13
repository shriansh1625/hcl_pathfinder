from app.core.enums import EligibilityStatus, PathItemKind, PrerequisiteEvidenceState, RequiredStatus
from app.core.skill_state import resolve_skill_status
from app.ontology.load import ResourcePrereqSpec, ResourceSkillSpec, ResourceSpec, load_ontology
from app.ontology.validate import validate_ontology
from app.services.catalog.audit import audit_catalog, classify_url
from app.services.gap_engine.profile import build_gap_profile
from app.services.path.generator import generate_path, select_for_path
from app.services.path.quality import validate_path
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.recommendation.config import load_recommendation_config
from app.services.recommendation.eligibility import evaluate_resource
from app.services.recommendation.models import LearnerPreferences, ScoreBreakdown, ScoredCandidate
from app.services.recommendation.scorer import score_candidates, score_resource
from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet
from app.services.skill_graph.dependency import SkillEdge


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


def _aiml_profile(fused: dict[str, FusedSkill]):
    bundle = load_ontology()
    role = next(item for item in bundle.roles if item.slug == "ai-ml-engineer")
    competencies = tuple(
        RoleCompetency(s.slug, s.slug, s.target_level, s.importance, RequiredStatus(s.required_status))
        for s in role.skills
    )
    edges = [SkillEdge(rel.source, rel.target, rel.type, rel.strength) for rel in bundle.relationships]
    profile = build_gap_profile(
        fused_by_slug=fused,
        role=RoleCompetencySet(role.slug, role.name, competencies),
        edges=edges,
    )
    return bundle, profile, edges


def _item_slugs(path):
    return [item.candidate.resource.slug for item in path.items if item.candidate]


def _item_skills(path):
    skills = []
    for item in path.items:
        if item.gate is not None:
            skills.append(item.gate.skill_slug)
        elif item.candidate is not None:
            skills.append(item.candidate.primary_skill)
    return skills


def test_url_status_validation_distinguishes_format_from_https_claim():
    bundle = load_ontology()
    errors = validate_ontology(bundle)
    assert errors == []
    audit = audit_catalog(bundle)
    assert audit.errors == ()
    assert 50 <= audit.resource_count <= 75
    for resource in bundle.resources:
        classified = classify_url(resource)
        if resource.url_status == "verified":
            assert classified.format_valid
            assert classified.classification == "VERIFIED_RESOURCE"
            assert resource.url and resource.url.startswith("https://")
        if resource.url_status == "claimed":
            assert classified.format_valid
            assert classified.classification == "CLAIMED_RESOURCE"
            assert resource.url and resource.url.startswith("https://")
        if resource.url_status == "unavailable":
            assert resource.url is None
            assert classified.classification == "UNAVAILABLE"
        assert classified.classification != "URL_CLAIMED_VERIFIED_RESOURCE"


def test_resource_causality_maps_to_role_skills():
    bundle = load_ontology()
    kaggle = next(item for item in bundle.resources if item.slug == "kaggle-intro-ml")
    aiml = next(item for item in bundle.roles if item.slug == "ai-ml-engineer")
    role_skills = {row.slug: row.importance for row in aiml.skills}
    covered = [row.slug for row in kaggle.skills if row.slug in role_skills]
    assert "ml_fundamentals" in covered
    assert role_skills["ml_fundamentals"] >= 0.90
    assert any(row.coverage_strength >= 0.70 for row in kaggle.skills if row.slug == "ml_fundamentals")


def test_path_causality_metadata_is_structured_and_not_score_only():
    bundle, profile, edges = _aiml_profile(
        {
            "python": _fused("python", 0.45),
            "statistics": _fused("statistics", 0.90),
            "ml_fundamentals": _fused("ml_fundamentals", 0.30),
        }
    )
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "READING"))
    assert path.items
    assert path.quality is not None
    for item in path.items:
        cause = item.cause
        assert cause is not None
        assert cause.why_selected
        assert cause.why_this_skill
        assert cause.why_this_position
        assert cause.why_this_intervention
        assert cause.why_this_resource
        assert cause.why_not_earlier
        assert "scored highly" not in cause.why_selected.lower()
        if item.kind == PathItemKind.VERIFICATION_GATE.value:
            assert "not a learning resource" in cause.why_this_intervention.lower()
        else:
            assert "coverage" in cause.why_this_resource.lower() or "maps to" in cause.why_this_resource.lower()


def test_irrelevant_resource_with_high_score_is_rejected():
    stats = RoleCompetency("statistics", "Statistics", 0.8, 0.9, RequiredStatus.CORE)
    profile = build_gap_profile(
        fused_by_slug={"statistics": _fused("statistics", 0.3)},
        role=RoleCompetencySet("aiml", "AI/ML", (stats,)),
        edges=[],
    )
    relevant = _resource("stats-course", "statistics", coverage=0.85)
    impostor = _resource("impostor", "statistics", coverage=0.99)
    prefs = LearnerPreferences(8, "HANDS_ON")
    scored = score_candidates([relevant, impostor], profile, prefs)
    impostor_scored = next(item for item in scored if item.resource.slug == "impostor")
    fake_high = ScoredCandidate(
        resource=impostor_scored.resource,
        primary_skill=impostor_scored.primary_skill,
        eligibility=impostor_scored.eligibility,
        intervention=impostor_scored.intervention,
        breakdown=ScoreBreakdown(
            skill_gap_fit=0.99,
            role_importance=0.0,
            prerequisite_fit=1.0,
            difficulty_fit=1.0,
            duration_fit=1.0,
            learning_style_fit=1.0,
            semantic_similarity=0.99,
            final_score=0.92,
        ),
        explanation=impostor_scored.explanation,
    )
    cfg = load_recommendation_config()
    selected = select_for_path(
        [fake_high, *[item for item in scored if item.resource.slug == "stats-course"]],
        profile,
        weekly_hours=8,
        max_items=cfg.max_items,
        horizon_weeks=cfg.horizon_weeks,
    )
    slugs = [item.resource.slug for item in selected]
    assert "impostor" not in slugs
    assert "stats-course" in slugs


def test_blocker_chain_python_ml_deep_learning_from_graph():
    python = _resource("python-course", "python", coverage=0.9)
    ml = _resource("ml-course", "ml_fundamentals", coverage=0.9, prereqs=[("python", 0.7)])
    dl = _resource("dl-course", "neural_networks", coverage=0.9, difficulty=4, prereqs=[("ml_fundamentals", 0.5)])
    role = RoleCompetencySet(
        "r",
        "R",
        (
            RoleCompetency("python", "Python", 0.85, 0.95, RequiredStatus.CORE),
            RoleCompetency("ml_fundamentals", "ML", 0.85, 0.95, RequiredStatus.CORE),
            RoleCompetency("neural_networks", "DL", 0.80, 0.90, RequiredStatus.CORE),
        ),
    )
    edges = [
        SkillEdge("python", "ml_fundamentals", "HARD_PREREQUISITE", 0.95),
        SkillEdge("ml_fundamentals", "neural_networks", "HARD_PREREQUISITE", 0.90),
    ]
    profile = build_gap_profile(
        fused_by_slug={
            "python": _fused("python", 0.30),
            "ml_fundamentals": _fused("ml_fundamentals", 0.25),
            "neural_networks": _fused("neural_networks", 0.20),
        },
        role=role,
        edges=edges,
    )
    path = generate_path(profile, [python, ml, dl], edges, LearnerPreferences(12, "READING"))
    slugs = _item_slugs(path)
    assert slugs.index("python-course") < slugs.index("ml-course")
    assert slugs.index("python-course") < slugs.index("dl-course")


def test_unknown_docker_unblock_chain_is_visible():
    bundle, profile, edges = _aiml_profile(
        {
            "python": _fused("python", 0.80),
            "model_deployment": _fused("model_deployment", 0.30),
            "supervised_learning": _fused("supervised_learning", 0.70),
        }
    )
    docker_res = next(item for item in bundle.resources if item.slug == "docker-compose-guide")
    unknown = evaluate_resource(docker_res, {"docker": None})
    assert unknown.status is EligibilityStatus.BLOCKED_BY_UNKNOWN
    assert unknown.checks[0].state is PrerequisiteEvidenceState.UNKNOWN
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "MIXED"))
    skills = _item_skills(path)
    assert "docker" in skills
    docker_gate = next(
        item
        for item in path.items
        if item.kind == PathItemKind.VERIFICATION_GATE.value
        and item.gate
        and item.gate.skill_slug == "docker"
    )
    assert docker_gate.candidate is None
    assert docker_gate.cause is not None
    assert "unknown" in docker_gate.cause.why_selected.lower() or "docker" in docker_gate.cause.why_this_skill.lower()
    waiting_slugs = {
        item.candidate.resource.slug
        for item in path.items
        if not item.executable and item.candidate is not None
    }
    executable_slugs = {
        item.candidate.resource.slug
        for item in path.items
        if item.executable and item.candidate is not None
    }
    assert "serve-sklearn-model-lab" not in executable_slugs
    assert "docker-get-started" not in executable_slugs
    assert "serve-sklearn-model-lab" in waiting_slugs or any(
        item.kind == PathItemKind.WAITING_FOR_VERIFICATION.value for item in path.items
    )


def test_dependency_order_not_score_order():
    python = _resource("python-course", "python", coverage=0.9, difficulty=2)
    ml = _resource("ml-course", "ml_fundamentals", coverage=0.9, difficulty=3, prereqs=[("python", 0.7)])
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
        fused_by_slug={
            "python": _fused("python", 0.45),
            "ml_fundamentals": _fused("ml_fundamentals", 0.30),
        },
        role=role,
        edges=edges,
    )
    prefs = LearnerPreferences(10, "READING")
    scored = score_candidates([python, ml], profile, prefs)
    path = generate_path(profile, [python, ml], edges, prefs)
    ordered = _item_slugs(path)
    assert ordered.index("python-course") < ordered.index("ml-course")
    by_score = [item.resource.slug for item in scored]
    if by_score[0] == "ml-course":
        assert ordered[0] == "python-course"


def test_time_budget_changes_journey_not_just_week_labels():
    bundle, profile, edges = _aiml_profile(
        {
            "python": _fused("python", 0.40),
            "statistics": _fused("statistics", 0.30),
            "ml_fundamentals": _fused("ml_fundamentals", 0.20),
            "model_deployment": _fused("model_deployment", 0.30),
            "neural_networks": _fused("neural_networks", 0.20),
        }
    )
    five = generate_path(profile, bundle.resources, edges, LearnerPreferences(5, "MIXED"))
    eight = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "MIXED"))
    fifteen = generate_path(profile, bundle.resources, edges, LearnerPreferences(15, "MIXED"))
    def slugs(path):
        return _item_slugs(path)

    assert slugs(five) != slugs(fifteen) or len(five.items) != len(fifteen.items)
    assert slugs(five) != slugs(eight) or slugs(eight) != slugs(fifteen) or len(five.items) != len(eight.items)


def test_learning_style_ranks_but_cannot_beat_role_and_gap():
    bundle, profile, edges = _aiml_profile({"statistics": _fused("statistics", 0.35)})
    _ = edges
    khan = next(item for item in bundle.resources if item.slug == "khan-statistics-probability")
    juice = next(item for item in bundle.resources if item.slug == "owasp-juice-shop")
    hands = LearnerPreferences(8, "HANDS_ON")
    khan_score = score_resource(khan, profile, hands)
    juice_score = score_resource(juice, profile, hands)
    assert juice_score.breakdown.learning_style_fit >= khan_score.breakdown.learning_style_fit
    assert khan_score.breakdown.role_importance > juice_score.breakdown.role_importance
    assert khan_score.breakdown.final_score > juice_score.breakdown.final_score
    path = generate_path(profile, bundle.resources, edges, hands)
    slugs = _item_slugs(path)
    assert "owasp-juice-shop" not in slugs


def test_different_roles_change_candidates_and_paths():
    fused = {
        "python": _fused("python", 0.90),
        "statistics": _fused("statistics", 0.35),
        "ml_fundamentals": _fused("ml_fundamentals", 0.55),
    }
    bundle = load_ontology()
    edges = [SkillEdge(rel.source, rel.target, rel.type, rel.strength) for rel in bundle.relationships]
    prefs = LearnerPreferences(8, "READING")

    def for_role(slug: str):
        role = next(item for item in bundle.roles if item.slug == slug)
        competencies = tuple(
            RoleCompetency(s.slug, s.slug, s.target_level, s.importance, RequiredStatus(s.required_status))
            for s in role.skills
        )
        profile = build_gap_profile(
            fused_by_slug=fused,
            role=RoleCompetencySet(role.slug, role.name, competencies),
            edges=edges,
        )
        return generate_path(profile, bundle.resources, edges, prefs)

    aiml = for_role("ai-ml-engineer")
    cyber = for_role("cybersecurity-analyst")
    assert set(_item_slugs(aiml)) != set(_item_slugs(cyber)) or _item_skills(aiml) != _item_skills(cyber)
    assert _item_skills(aiml) != _item_skills(cyber)


def test_different_learners_change_interventions_and_order():
    bundle = load_ontology()
    edges = [SkillEdge(rel.source, rel.target, rel.type, rel.strength) for rel in bundle.relationships]
    prefs = LearnerPreferences(8, "READING")
    a = generate_path(
        _aiml_profile(
            {
                "python": _fused("python", 0.90),
                "statistics": _fused("statistics", 0.35),
                "ml_fundamentals": _fused("ml_fundamentals", 0.55),
            }
        )[1],
        bundle.resources,
        edges,
        prefs,
    )
    b = generate_path(
        _aiml_profile(
            {
                "python": _fused("python", 0.45),
                "statistics": _fused("statistics", 0.90),
                "ml_fundamentals": _fused("ml_fundamentals", 0.30),
            }
        )[1],
        bundle.resources,
        edges,
        prefs,
    )
    c = generate_path(
        _aiml_profile(
            {
                "python": _fused("python", 0.70),
                "statistics": _fused("statistics", 0.65),
                "ml_fundamentals": _fused("ml_fundamentals", 0.60),
                "model_deployment": _fused("model_deployment", 0.30),
            }
        )[1],
        bundle.resources,
        edges,
        prefs,
    )
    slugs = lambda path: _item_slugs(path)
    assert slugs(a) != slugs(b)
    assert slugs(b) != slugs(c) or [
        item.candidate.intervention for item in a.items if item.candidate
    ] != [item.candidate.intervention for item in c.items if item.candidate]
    assert "fastapi-tutorial" not in slugs(c)


def test_deterministic_generation_ignores_identity_fields():
    bundle, profile, edges = _aiml_profile(
        {"python": _fused("python", 0.45), "ml_fundamentals": _fused("ml_fundamentals", 0.30)}
    )
    prefs = LearnerPreferences(8, "HANDS_ON")
    first = generate_path(profile, bundle.resources, edges, prefs)
    second = generate_path(profile, bundle.resources, edges, prefs)
    key = lambda path: [
        (
            item.gate.skill_slug if item.gate else item.candidate.resource.slug,
            item.week_index,
            item.position,
            item.kind,
            item.cause.why_selected if item.cause else "",
        )
        for item in path.items
    ]
    assert key(first) == key(second)


def test_resource_diversity_is_same_skill_journey_not_filler():
    python_course = _resource("python-course", "python", coverage=0.9, rtype="course")
    python_lab = _resource("python-lab", "python", coverage=0.8, rtype="lab", modes=["lab"])
    python_assess = _resource("python-assess", "python", coverage=0.7, rtype="assessment", duration=0.5)
    filler = _resource("random-lab", "git", coverage=0.9, rtype="lab", modes=["lab"])
    role = RoleCompetencySet(
        "r",
        "R",
        (
            RoleCompetency("python", "Python", 0.85, 0.95, RequiredStatus.CORE),
            RoleCompetency("git", "Git", 0.60, 0.40, RequiredStatus.ELECTIVE),
        ),
    )
    profile = build_gap_profile(
        fused_by_slug={"python": _fused("python", 0.40)},
        role=role,
        edges=[],
    )
    path = generate_path(
        profile,
        [python_course, python_lab, python_assess, filler],
        [],
        LearnerPreferences(10, "HANDS_ON"),
    )
    slugs = _item_slugs(path)
    types = [item.candidate.resource.type for item in path.items if item.candidate]
    assert "python-course" in slugs or "python-lab" in slugs
    assert "python-lab" in slugs or "python-assess" in slugs
    assert "python-course" in slugs
    assert "random-lab" not in slugs
    assert types != ["course"] * len(types) or len(types) == 1


def test_target_met_skill_does_not_consume_the_path():
    bundle, profile, edges = _aiml_profile(
        {
            "python": _fused("python", 0.95),
            "statistics": _fused("statistics", 0.35),
        }
    )
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "READING"))
    python_primaries = [
        item
        for item in path.items
        if item.candidate is not None and item.candidate.primary_skill == "python"
    ]
    assert python_primaries == []
    skills = _item_skills(path)
    assert "statistics" in skills


def test_score_vs_causality_conflict_prefers_blocker():
    python = _resource("python-course", "python", coverage=0.8, duration=3)
    fancy = _resource("fancy-ml", "ml_fundamentals", coverage=0.99, difficulty=5, duration=3)
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
        fused_by_slug={
            "python": _fused("python", 0.40),
            "ml_fundamentals": _fused("ml_fundamentals", 0.25),
        },
        role=role,
        edges=edges,
    )
    path = generate_path(profile, [python, fancy], edges, LearnerPreferences(8, "READING"))
    slugs = _item_slugs(path)
    assert slugs[0] == "python-course"
    report = validate_path(list(path.items), profile, [python, fancy], edges, weekly_hours=8)
    assert report.ROLE_RELEVANCE_VALID
    assert report.RESOURCE_VALID
    assert report.SEQUENCE_VALID
    assert report.EXPLANATION_GROUNDED
