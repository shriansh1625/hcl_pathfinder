from __future__ import annotations

from collections import defaultdict

from app.core.enums import RelationshipType, RequiredStatus, ResourceType, UrlStatus
from app.ontology.load import OntologyBundle


class OntologyValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("Ontology validation failed:\n" + "\n".join(f"- {e}" for e in errors))


def _unit_interval(name: str, value: float, errors: list[str]) -> None:
    if not 0.0 <= value <= 1.0:
        errors.append(f"{name} must be in [0, 1], got {value}")


def hard_prerequisite_cycles(bundle: OntologyBundle) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for rel in bundle.relationships:
        if rel.type != RelationshipType.HARD_PREREQUISITE:
            continue
        graph[rel.source].append(rel.target)
        nodes.add(rel.source)
        nodes.add(rel.target)

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        visiting.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt in visiting:
                start = stack.index(nxt)
                cycles.append(stack[start:] + [nxt])
            elif nxt not in visited:
                dfs(nxt)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(nodes):
        if node not in visited:
            dfs(node)
    return cycles


def validate_ontology(bundle: OntologyBundle) -> list[str]:
    errors: list[str] = []
    slugs = [s.slug for s in bundle.skills]
    names = [s.canonical_name.lower() for s in bundle.skills]
    skill_set = set(slugs)

    if len(slugs) != len(set(slugs)):
        seen: set[str] = set()
        for slug in slugs:
            if slug in seen:
                errors.append(f"Duplicate skill ID: {slug}")
            seen.add(slug)

    if len(names) != len(set(names)):
        seen_names: set[str] = set()
        for name in names:
            if name in seen_names:
                errors.append(f"Duplicate canonical name: {name}")
            seen_names.add(name)

    valid_rel = {item.value for item in RelationshipType}
    valid_req = {item.value for item in RequiredStatus}
    valid_types = {item.value for item in ResourceType}
    valid_url = {item.value for item in UrlStatus}

    for rel in bundle.relationships:
        if rel.source == rel.target:
            errors.append(f"Self-reference: {rel.source} -> {rel.target}")
        if rel.source not in skill_set:
            errors.append(f"Relationship source missing skill: {rel.source}")
        if rel.target not in skill_set:
            errors.append(f"Relationship target missing skill: {rel.target}")
        if rel.type not in valid_rel:
            errors.append(f"Invalid relationship type {rel.type} on {rel.source}->{rel.target}")
        _unit_interval(f"relationship strength {rel.source}->{rel.target}", rel.strength, errors)

    for cycle in hard_prerequisite_cycles(bundle):
        errors.append("HARD_PREREQUISITE cycle: " + " -> ".join(cycle))

    role_slugs = [r.slug for r in bundle.roles]
    if len(role_slugs) != len(set(role_slugs)):
        errors.append("Duplicate role IDs found")
    if len(role_slugs) != 5:
        errors.append(f"Expected 5 roles, found {len(role_slugs)}")

    referenced_by_role: set[str] = set()
    for role in bundle.roles:
        if not role.skills:
            errors.append(f"Role {role.slug} has no skills")
        seen_role_skills: set[str] = set()
        for rs in role.skills:
            if rs.slug in seen_role_skills:
                errors.append(f"Duplicate role skill {rs.slug} on {role.slug}")
            seen_role_skills.add(rs.slug)
            referenced_by_role.add(rs.slug)
            if rs.slug not in skill_set:
                errors.append(f"Role {role.slug} references missing skill {rs.slug}")
            if rs.required_status not in valid_req:
                errors.append(f"Invalid required_status {rs.required_status} on {role.slug}/{rs.slug}")
            _unit_interval(f"{role.slug}.{rs.slug} target_level", rs.target_level, errors)
            _unit_interval(f"{role.slug}.{rs.slug} importance", rs.importance, errors)

    resource_slugs = [r.slug for r in bundle.resources]
    if len(resource_slugs) != len(set(resource_slugs)):
        errors.append("Duplicate resource IDs found")

    referenced_by_resource: set[str] = set()
    for resource in bundle.resources:
        if resource.type not in valid_types:
            errors.append(f"Invalid resource type {resource.type} on {resource.slug}")
        if resource.url_status not in valid_url:
            errors.append(f"Invalid url_status {resource.url_status} on {resource.slug}")
        if resource.url_status == UrlStatus.VERIFIED and not resource.url:
            errors.append(f"Verified resource {resource.slug} is missing a URL")
        if resource.url_status == UrlStatus.UNAVAILABLE and resource.url:
            errors.append(f"Unavailable resource {resource.slug} should not invent a URL")
        if resource.duration_hours <= 0:
            errors.append(f"Invalid duration_hours on {resource.slug}")
        if not 1 <= resource.difficulty <= 5:
            errors.append(f"Invalid difficulty on {resource.slug}")
        allowed_modes = {"reading", "video", "project", "lab"}
        for mode in resource.learning_modes:
            if mode not in allowed_modes:
                errors.append(f"Invalid learning mode {mode} on {resource.slug}")
        for rs in resource.skills:
            referenced_by_resource.add(rs.slug)
            if rs.slug not in skill_set:
                errors.append(f"Resource {resource.slug} references missing skill {rs.slug}")
            _unit_interval(f"{resource.slug} coverage {rs.slug}", rs.coverage_strength, errors)
            _unit_interval(f"{resource.slug} delta {rs.slug}", rs.expected_level_delta, errors)
        for prereq in resource.prerequisites:
            if prereq.slug not in skill_set:
                errors.append(
                    f"Resource {resource.slug} prerequisite missing skill {prereq.slug}"
                )
            _unit_interval(f"{resource.slug} prereq {prereq.slug}", prereq.min_level, errors)

    assessment_slugs = [a.slug for a in bundle.assessments]
    if len(assessment_slugs) != len(set(assessment_slugs)):
        errors.append("Duplicate assessment IDs found")

    referenced_by_assessment: set[str] = set()
    for assessment in bundle.assessments:
        if assessment.primary_skill not in skill_set:
            errors.append(
                f"Assessment {assessment.slug} primary skill missing: {assessment.primary_skill}"
            )
        referenced_by_assessment.add(assessment.primary_skill)
        _unit_interval(f"{assessment.slug} pass_threshold", assessment.pass_threshold, errors)
        if not assessment.questions:
            errors.append(f"Assessment {assessment.slug} has no questions")
        for idx, question in enumerate(assessment.questions):
            if question.skill not in skill_set:
                errors.append(
                    f"Assessment {assessment.slug} question {idx} missing skill {question.skill}"
                )
            referenced_by_assessment.add(question.skill)
            if not question.choices:
                errors.append(f"Assessment {assessment.slug} question {idx} has no choices")
            if question.correct_index < 0 or question.correct_index >= len(question.choices):
                errors.append(
                    f"Assessment {assessment.slug} question {idx} has invalid correct_index"
                )
            if not 1 <= question.difficulty <= 5:
                errors.append(f"Assessment {assessment.slug} question {idx} invalid difficulty")

    related_in_graph = {rel.source for rel in bundle.relationships} | {
        rel.target for rel in bundle.relationships
    }
    for skill in bundle.skills:
        used = (
            skill.slug in referenced_by_role
            or skill.slug in related_in_graph
            or skill.slug in referenced_by_resource
            or skill.slug in referenced_by_assessment
        )
        if not used:
            errors.append(f"Orphan skill (unreferenced): {skill.slug}")

    return errors


def assert_valid(bundle: OntologyBundle) -> None:
    errors = validate_ontology(bundle)
    if errors:
        raise OntologyValidationError(errors)
