from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.core.paths import DATA_DIR


@dataclass
class SkillSpec:
    slug: str
    canonical_name: str
    category: str
    description: str


@dataclass
class RelationshipSpec:
    source: str
    target: str
    type: str
    strength: float
    rationale: str


@dataclass
class RoleSkillSpec:
    slug: str
    target_level: float
    importance: float
    required_status: str


@dataclass
class RoleSpec:
    slug: str
    name: str
    description: str
    skills: list[RoleSkillSpec]


@dataclass
class ResourceSkillSpec:
    slug: str
    coverage_strength: float
    expected_level_delta: float
    is_primary: bool = False


@dataclass
class ResourcePrereqSpec:
    slug: str
    min_level: float


@dataclass
class ResourceSpec:
    slug: str
    title: str
    description: str
    type: str
    difficulty: int
    duration_hours: float
    source: str
    url: str | None
    url_status: str
    learning_modes: list[str]
    is_active: bool
    skills: list[ResourceSkillSpec]
    prerequisites: list[ResourcePrereqSpec]


@dataclass
class QuestionSpec:
    prompt: str
    skill: str
    difficulty: int
    choices: list[str]
    correct_index: int
    explanation: str
    concept_tag: str


@dataclass
class AssessmentSpec:
    slug: str
    title: str
    description: str
    primary_skill: str
    pass_threshold: float
    questions: list[QuestionSpec]


@dataclass
class OntologyBundle:
    skills: list[SkillSpec]
    relationships: list[RelationshipSpec]
    roles: list[RoleSpec]
    resources: list[ResourceSpec]
    assessments: list[AssessmentSpec]
    errors: list[str] = field(default_factory=list)


def _load_yaml(path: Path) -> dict | list:
    if not path.exists():
        raise FileNotFoundError(f"Missing ontology file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_ontology(data_dir: Path | None = None) -> OntologyBundle:
    root = data_dir or DATA_DIR
    skills_raw = _load_yaml(root / "ontology" / "skills.yaml")
    rel_raw = _load_yaml(root / "ontology" / "relationships.yaml")
    roles_raw = _load_yaml(root / "ontology" / "roles.yaml")
    resources_raw = _load_yaml(root / "catalog" / "resources.yaml")

    skills = [
        SkillSpec(
            slug=item["slug"],
            canonical_name=item["canonical_name"],
            category=item["category"],
            description=item["description"].strip(),
        )
        for item in skills_raw["skills"]
    ]
    relationships = [
        RelationshipSpec(
            source=item["source"],
            target=item["target"],
            type=item["type"],
            strength=float(item["strength"]),
            rationale=item["rationale"].strip(),
        )
        for item in rel_raw["relationships"]
    ]
    roles = []
    for item in roles_raw["roles"]:
        role_skills = [
            RoleSkillSpec(
                slug=s["slug"],
                target_level=float(s["target_level"]),
                importance=float(s["importance"]),
                required_status=s["required_status"],
            )
            for s in item["skills"]
        ]
        roles.append(
            RoleSpec(
                slug=item["slug"],
                name=item["name"],
                description=item["description"].strip(),
                skills=role_skills,
            )
        )

    resources = []
    for item in resources_raw["resources"]:
        resources.append(
            ResourceSpec(
                slug=item["slug"],
                title=item["title"],
                description=item["description"].strip(),
                type=item["type"],
                difficulty=int(item["difficulty"]),
                duration_hours=float(item["duration_hours"]),
                source=item["source"],
                url=item.get("url"),
                url_status=item["url_status"],
                learning_modes=list(item.get("learning_modes") or []),
                is_active=bool(item.get("is_active", True)),
                skills=[
                    ResourceSkillSpec(
                        slug=s["slug"],
                        coverage_strength=float(s["coverage_strength"]),
                        expected_level_delta=float(s["expected_level_delta"]),
                        is_primary=bool(s.get("is_primary", False)),
                    )
                    for s in item.get("skills") or []
                ],
                prerequisites=[
                    ResourcePrereqSpec(slug=p["slug"], min_level=float(p["min_level"]))
                    for p in item.get("prerequisites") or []
                ],
            )
        )

    assessments: list[AssessmentSpec] = []
    for path in sorted((root / "assessments").glob("*.yaml")):
        raw = _load_yaml(path)
        item = raw["assessment"]
        questions = [
            QuestionSpec(
                prompt=q["prompt"].strip(),
                skill=q["skill"],
                difficulty=int(q["difficulty"]),
                choices=list(q["choices"]),
                correct_index=int(q["correct_index"]),
                explanation=q["explanation"].strip(),
                concept_tag=q["concept_tag"],
            )
            for q in item["questions"]
        ]
        assessments.append(
            AssessmentSpec(
                slug=item["slug"],
                title=item["title"],
                description=item["description"].strip(),
                primary_skill=item["primary_skill"],
                pass_threshold=float(item["pass_threshold"]),
                questions=questions,
            )
        )

    return OntologyBundle(
        skills=skills,
        relationships=relationships,
        roles=roles,
        resources=resources,
        assessments=assessments,
    )
