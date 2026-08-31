"""Read-only role catalog from the validated YAML ontology (no database required)."""

from __future__ import annotations

from app.core.ids import ontology_uuid
from app.ontology.load import load_ontology
from app.schemas import RoleRead
from app.schemas.intelligence import CompetencyRead, RoleCompetencyRead, RoleDetailRead


def _skill_names() -> dict[str, str]:
    bundle = load_ontology()
    return {item.slug: item.canonical_name for item in bundle.skills}


def list_roles_from_ontology() -> list[RoleRead]:
    bundle = load_ontology()
    return [
        RoleRead(
            id=ontology_uuid("role", role.slug),
            slug=role.slug,
            name=role.name,
            description=role.description.strip(),
        )
        for role in sorted(bundle.roles, key=lambda item: item.name)
    ]


def role_competencies_from_ontology(role_slug: str) -> RoleCompetencyRead:
    bundle = load_ontology()
    role = next((item for item in bundle.roles if item.slug == role_slug), None)
    if role is None:
        raise KeyError(f"Unknown role: {role_slug}")
    names = _skill_names()
    return RoleCompetencyRead(
        role=role.slug,
        name=role.name,
        competencies=[
            CompetencyRead(
                skill=item.slug,
                name=names.get(item.slug, item.slug.replace("_", " ").title()),
                target_level=item.target_level,
                importance=item.importance,
                required_status=item.required_status,
            )
            for item in role.skills
        ],
    )


def role_detail_from_ontology(role_slug: str) -> RoleDetailRead:
    bundle = load_ontology()
    role = next((item for item in bundle.roles if item.slug == role_slug), None)
    if role is None:
        raise KeyError(f"Unknown role: {role_slug}")
    profile = role_competencies_from_ontology(role_slug)
    core = [item.skill for item in profile.competencies if item.required_status == "CORE"][:8]
    categories = sorted({item.name.split()[0] for item in profile.competencies[:6]})
    return RoleDetailRead(
        slug=role.slug,
        name=role.name,
        description=role.description.strip(),
        competency_count=len(profile.competencies),
        core_skills=core,
        focus_areas=categories,
    )
