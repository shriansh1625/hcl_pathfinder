from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import RequiredStatus


@dataclass(frozen=True)
class RoleCompetency:
    skill_slug: str
    skill_name: str
    target_level: float
    importance: float
    required_status: RequiredStatus


@dataclass(frozen=True)
class RoleCompetencySet:
    role_slug: str
    role_name: str
    competencies: tuple[RoleCompetency, ...]

    def by_slug(self) -> dict[str, RoleCompetency]:
        return {item.skill_slug: item for item in self.competencies}

    def slugs(self) -> set[str]:
        return {item.skill_slug for item in self.competencies}
