"""Path V1 → V2 diff model. Deterministic reasons from state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiffEntry:
    key: str
    skill: str
    title: str
    reason: str
    from_week: int | None = None
    to_week: int | None = None

    def as_dict(self) -> dict:
        payload = {
            "key": self.key,
            "skill": self.skill,
            "title": self.title,
            "reason": self.reason,
        }
        if self.from_week is not None or self.to_week is not None:
            payload["from_week"] = self.from_week
            payload["to_week"] = self.to_week
        return payload


@dataclass(frozen=True)
class PathDiff:
    added: tuple[DiffEntry, ...] = ()
    removed: tuple[DiffEntry, ...] = ()
    moved: tuple[DiffEntry, ...] = ()
    unchanged: tuple[DiffEntry, ...] = ()
    blocked: tuple[DiffEntry, ...] = ()
    changed_skills: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.moved or self.blocked)

    def as_dict(self) -> dict:
        return {
            "added": [entry.as_dict() for entry in self.added],
            "removed": [entry.as_dict() for entry in self.removed],
            "moved": [entry.as_dict() for entry in self.moved],
            "unchanged": [entry.as_dict() for entry in self.unchanged],
            "blocked": [entry.as_dict() for entry in self.blocked],
            "changed_skills": list(self.changed_skills),
        }
