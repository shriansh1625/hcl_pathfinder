from app.core.enums import RelationshipType
from app.ontology.load import (
    OntologyBundle,
    RelationshipSpec,
    RoleSkillSpec,
    RoleSpec,
    SkillSpec,
    load_ontology,
)
from app.ontology.validate import hard_prerequisite_cycles, validate_ontology


def test_seed_yaml_is_valid():
    bundle = load_ontology()
    errors = validate_ontology(bundle)
    assert errors == []
    assert 50 <= len(bundle.resources) <= 75


def test_skill_and_role_uniqueness():
    bundle = load_ontology()
    slugs = [s.slug for s in bundle.skills]
    names = [s.canonical_name.lower() for s in bundle.skills]
    roles = [r.slug for r in bundle.roles]
    assert len(slugs) == len(set(slugs))
    assert len(names) == len(set(names))
    assert len(roles) == len(set(roles))
    assert len(roles) == 8


def test_hard_prerequisite_graph_is_acyclic():
    bundle = load_ontology()
    assert hard_prerequisite_cycles(bundle) == []


def test_relationship_types_are_known():
    bundle = load_ontology()
    allowed = {item.value for item in RelationshipType}
    for rel in bundle.relationships:
        assert rel.type in allowed
        assert rel.source != rel.target


def test_resource_and_assessment_skill_references_exist():
    bundle = load_ontology()
    skills = {s.slug for s in bundle.skills}
    for resource in bundle.resources:
        for rs in resource.skills:
            assert rs.slug in skills
        for prereq in resource.prerequisites:
            assert prereq.slug in skills
    for assessment in bundle.assessments:
        assert assessment.primary_skill in skills
        for question in assessment.questions:
            assert question.skill in skills


def test_cycle_detector_fails_on_hard_loop():
    skills = [
        SkillSpec("a", "A", "X", "a"),
        SkillSpec("b", "B", "X", "b"),
    ]
    rels = [
        RelationshipSpec("a", "b", "HARD_PREREQUISITE", 1.0, "loop"),
        RelationshipSpec("b", "a", "HARD_PREREQUISITE", 1.0, "loop"),
    ]
    roles = [
        RoleSpec(
            "r",
            "R",
            "d",
            [RoleSkillSpec("a", 0.5, 0.5, "CORE"), RoleSkillSpec("b", 0.5, 0.5, "CORE")],
        )
    ]
    bundle = OntologyBundle(skills, rels, roles, [], [])
    errors = validate_ontology(bundle)
    assert any("cycle" in e.lower() for e in errors)


def test_self_reference_is_rejected():
    skills = [SkillSpec("a", "A", "X", "a")]
    rels = [RelationshipSpec("a", "a", "RELATED", 0.5, "self")]
    roles = [RoleSpec("r", "R", "d", [RoleSkillSpec("a", 0.5, 0.5, "CORE")])]
    bundle = OntologyBundle(skills, rels, roles, [], [])
    errors = validate_ontology(bundle)
    assert any("Self-reference" in e for e in errors)
