"""Structured AI output. The LLM never writes learner or path state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal[
    "WHY_GAP",
    "WHY_RESOURCE",
    "WHAT_CHANGED",
    "NEXT_ACTION",
    "COACH",
    "QUERY",
]


class Fact(BaseModel):
    id: str
    label: str
    value: str


class Claim(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    fact_ids: list[str] = Field(min_length=1, max_length=12)


class GroundedAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=1800)
    claims: list[Claim] = Field(min_length=1, max_length=8)
    confidence: Literal["grounded"] = "grounded"
    source: Literal["llm", "deterministic"] = "deterministic"
    facts: list[Fact] = Field(default_factory=list)
    intent: str = "QUERY"


class AIContext(BaseModel):
    """Verified facts only. No secrets, sessions, or raw DB rows."""

    intent: Intent
    fingerprint: str
    learner: dict
    target_role: dict
    skill: dict | None = None
    dependencies: list[dict] = Field(default_factory=list)
    resource: dict | None = None
    path_item: dict | None = None
    next_action: dict | None = None
    adaptation: dict | None = None
    facts: list[Fact] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    allowed_resources: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_titles: list[str] = Field(default_factory=list)
    allowed_numbers: list[float] = Field(default_factory=list)

    def fact_ids(self) -> set[str]:
        return {item.id for item in self.facts}

    def facts_payload(self) -> list[dict[str, str]]:
        return [item.model_dump() for item in self.facts]
