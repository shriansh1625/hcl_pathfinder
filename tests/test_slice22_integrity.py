"""Slice 2.2: verification gates, path integrity, URL honesty, catalog cleanup."""

from __future__ import annotations

from app.core.enums import (
    ActionClass,
    EligibilityStatus,
    EvidenceState,
    GateState,
    PathItemKind,
    RequiredStatus,
    UrlStatus,
)
from app.core.skill_state import resolve_skill_status
from app.ontology.load import ResourcePrereqSpec, ResourceSkillSpec, ResourceSpec, load_ontology
from app.ontology.validate import validate_ontology
from app.services.assessment.contract import AssessmentResult, evidence_from_assessment
from app.services.catalog.audit import audit_catalog, classify_url
from app.services.gap_engine.profile import build_gap_profile
from app.services.path.generator import generate_path
from app.services.profiling.evidence_fusion import FusedSkill
from app.services.recommendation.eligibility import evaluate_resource, recompute_eligibility
from app.services.recommendation.models import LearnerPreferences
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


def _role_profile(role_slug: str, fused: dict[str, FusedSkill]):
    bundle = load_ontology()
    role = next(item for item in bundle.roles if item.slug == role_slug)
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


def _course(slug: str, skill: str, *, prereqs=None, difficulty: int = 2) -> ResourceSpec:
    return ResourceSpec(
        slug=slug,
        title=slug,
        description=slug,
        type="course",
        difficulty=difficulty,
        duration_hours=4,
        source="test",
        url=None,
        url_status="unavailable",
        learning_modes=["reading"],
        is_active=True,
        skills=[ResourceSkillSpec(skill, 0.9, 0.2, True)],
        prerequisites=[ResourcePrereqSpec(p[0], p[1]) for p in (prereqs or [])],
    )


def test_unknown_role_produces_verification_gates():
    bundle, profile, edges = _role_profile("cybersecurity-analyst", {})
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "MIXED"))
    gates = [item for item in path.items if item.kind == PathItemKind.VERIFICATION_GATE.value]
    assert gates
    skills = {item.gate.skill_slug for item in gates if item.gate}
    assert "networking_basics" in skills
    assert "linux" in skills
    assert "owasp_top10" in skills
    for item in gates:
        assert item.candidate is None
        assert item.executable is True
        assert item.gate is not None
        assert item.gate.state is GateState.PENDING
        assert item.cause is not None
        assert "UNKNOWN" in item.cause.why_selected


def test_unknown_does_not_become_numeric_gap():
    _bundle, profile, _edges = _role_profile("cybersecurity-analyst", {})
    networking = next(
        item for item in profile.items if item.ranked.gap.skill_slug == "networking_basics"
    )
    assert networking.ranked.gap.evidence_state is EvidenceState.UNKNOWN
    assert networking.ranked.gap.proficiency is None
    assert networking.ranked.gap.gap is None
    assert networking.ranked.gap_priority == 0.0
    assert networking.ranked.verification_priority > 0
    assert networking.action is ActionClass.VERIFY


def test_verify_is_not_a_learning_resource():
    bundle, profile, edges = _role_profile("cybersecurity-analyst", {})
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "MIXED"))
    for item in path.items:
        if item.kind != PathItemKind.VERIFICATION_GATE.value:
            continue
        assert item.candidate is None
        assert "not a learning resource" in item.cause.why_this_intervention.lower()
        assert item.gate is not None
        assert "http" not in item.cause.why_this_resource.lower()


def test_blocked_resource_is_not_executable_and_waiting_for_verification():
    bundle, profile, edges = _role_profile(
        "ai-ml-engineer",
        {
            "python": _fused("python", 0.80),
            "model_deployment": _fused("model_deployment", 0.30),
            "supervised_learning": _fused("supervised_learning", 0.70),
        },
    )
    lab = next(item for item in bundle.resources if item.slug == "serve-sklearn-model-lab")
    blocked = evaluate_resource(
        lab, {"docker": None, "python": 0.80, "supervised_learning": 0.70}
    )
    assert blocked.status is EligibilityStatus.BLOCKED_BY_UNKNOWN
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(8, "MIXED"))
    executable_slugs = {
        item.candidate.resource.slug
        for item in path.items
        if item.executable and item.candidate is not None
    }
    assert "serve-sklearn-model-lab" not in executable_slugs
    waiting = [
        item
        for item in path.items
        if item.kind == PathItemKind.WAITING_FOR_VERIFICATION.value
        and item.candidate is not None
        and item.candidate.resource.slug == "serve-sklearn-model-lab"
    ]
    assert waiting
    assert waiting[0].executable is False
    assert waiting[0].week_index is None
    assert any(
        item.kind == PathItemKind.VERIFICATION_GATE.value
        and item.gate
        and item.gate.skill_slug == "docker"
        for item in path.items
    )


def test_known_blocker_prevents_downstream_execution():
    bundle, profile, edges = _role_profile(
        "ai-ml-engineer",
        {
            "python": _fused("python", 0.30),
            "ml_fundamentals": _fused("ml_fundamentals", 0.25),
            "neural_networks": _fused("neural_networks", 0.20),
        },
    )
    path = generate_path(profile, bundle.resources, edges, LearnerPreferences(12, "READING"))
    executable_skills = {
        item.candidate.primary_skill
        for item in path.items
        if item.executable and item.candidate is not None
    }
    assert "python" in executable_skills
    for item in path.items:
        if item.candidate is None:
            continue
        if item.candidate.eligibility.status is EligibilityStatus.BLOCKED_BY_KNOWN_GAP:
            assert item.executable is False


def test_future_evidence_can_unlock_resource():
    bundle = load_ontology()
    lab = next(item for item in bundle.resources if item.slug == "serve-sklearn-model-lab")
    before = evaluate_resource(
        lab, {"docker": None, "python": 0.80, "supervised_learning": 0.70}
    )
    after = recompute_eligibility(
        lab, {"docker": 0.75, "python": 0.80, "supervised_learning": 0.70}
    )
    assert before.status is EligibilityStatus.BLOCKED_BY_UNKNOWN
    assert after.status is EligibilityStatus.ELIGIBLE
    result = AssessmentResult(
        assessment_slug="docker-check",
        skill_slug="docker",
        observed_level=0.75,
        confidence=0.9,
        passed=True,
    )
    evidence = evidence_from_assessment(result)
    assert evidence["skill"] == "docker"
    assert evidence["observed_level"] == 0.75
    assert evidence["source"] == "ASSESSMENT"


def test_hard_blocker_chain_is_not_all_executable():
    python = _course("python-course", "python")
    ml = _course("ml-course", "ml_fundamentals", prereqs=[("python", 0.7)], difficulty=3)
    dl = _course("dl-course", "neural_networks", prereqs=[("ml_fundamentals", 0.5)], difficulty=4)
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
    executable = [
        item.candidate.resource.slug
        for item in path.items
        if item.executable and item.candidate is not None
    ]
    waiting = [
        item.candidate.resource.slug
        for item in path.items
        if not item.executable and item.candidate is not None
    ]
    assert executable == ["python-course"]
    assert "ml-course" in waiting
    assert "dl-course" in waiting


def test_soft_prerequisite_does_not_hard_block():
    bundle = load_ontology()
    ml = next(item for item in bundle.resources if item.slug == "google-ml-crash-course")
    status = evaluate_resource(ml, {"python": 0.90, "statistics": None})
    assert not any(check.skill_slug == "statistics" for check in status.checks)
    assert status.status is EligibilityStatus.ELIGIBLE
    rel = next(
        item
        for item in bundle.relationships
        if item.source == "statistics" and item.target == "ml_fundamentals"
    )
    assert rel.type == "SOFT_PREREQUISITE"


def test_different_roles_produce_meaningful_output():
    fused = {
        "python": _fused("python", 0.90),
        "sql": _fused("sql", 0.75),
        "statistics": _fused("statistics", 0.35),
        "ml_fundamentals": _fused("ml_fundamentals", 0.55),
    }
    aiml_bundle, aiml_profile, edges = _role_profile("ai-ml-engineer", fused)
    cyber_bundle, cyber_profile, _ = _role_profile("cybersecurity-analyst", fused)
    aiml = generate_path(aiml_profile, aiml_bundle.resources, edges, LearnerPreferences(8, "READING"))
    cyber = generate_path(
        cyber_profile, cyber_bundle.resources, edges, LearnerPreferences(8, "READING")
    )
    aiml_exec = [
        item.candidate.resource.slug
        for item in aiml.items
        if item.executable and item.candidate is not None
    ]
    cyber_gates = [
        item.gate.skill_slug
        for item in cyber.items
        if item.kind == PathItemKind.VERIFICATION_GATE.value and item.gate
    ]
    assert aiml_exec
    assert cyber_gates
    assert "networking_basics" in cyber_gates or "owasp_top10" in cyber_gates
    assert set(aiml_exec) != {item.candidate.resource.slug for item in cyber.items if item.candidate}


def test_url_status_semantics_are_honest():
    bundle = load_ontology()
    assert validate_ontology(bundle) == []
    audit = audit_catalog(bundle)
    assert audit.errors == ()
    statuses = {item.url_status for item in bundle.resources}
    assert UrlStatus.CLAIMED.value in statuses
    assert UrlStatus.VERIFIED.value in statuses
    assert UrlStatus.UNAVAILABLE.value in statuses
    claimed = {item.slug for item in bundle.resources if item.url_status == "claimed"}
    assert "kaggle-intro-ml" in claimed
    assert "cloudflare-networking" in claimed
    for resource in bundle.resources:
        classified = classify_url(resource)
        if resource.url_status == "verified":
            assert classified.classification == "VERIFIED_RESOURCE"
            assert resource.url and resource.url.startswith("https://")
        if resource.url_status == "claimed":
            assert classified.classification == "CLAIMED_RESOURCE"
            assert resource.url and resource.url.startswith("https://")
        if resource.url_status == "unavailable":
            assert resource.url is None
            assert classified.classification == "UNAVAILABLE"
        assert classified.classification != "URL_CLAIMED_VERIFIED_RESOURCE"
