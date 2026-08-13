from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class LearningResource(TimestampMixin, Base):
    __tablename__ = "learning_resources"
    __table_args__ = (
        CheckConstraint("duration_hours > 0", name="duration_positive"),
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="difficulty_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    difficulty: Mapped[int] = mapped_column(nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_status: Mapped[str] = mapped_column(String(32), nullable=False)
    learning_modes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    resource_skills: Mapped[list[ResourceSkill]] = relationship(back_populates="resource")
    prerequisites: Mapped[list[ResourcePrerequisite]] = relationship(
        back_populates="resource"
    )


class ResourceSkill(Base):
    __tablename__ = "resource_skills"
    __table_args__ = (
        UniqueConstraint("resource_id", "skill_id", name="uq_resource_skills_pair"),
        CheckConstraint(
            "coverage_strength >= 0 AND coverage_strength <= 1",
            name="coverage_range",
        ),
        CheckConstraint(
            "expected_level_delta >= 0 AND expected_level_delta <= 1",
            name="delta_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    coverage_strength: Mapped[float] = mapped_column(Float, nullable=False)
    expected_level_delta: Mapped[float] = mapped_column(Float, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resource: Mapped[LearningResource] = relationship(back_populates="resource_skills")
    skill: Mapped["Skill"] = relationship()


class ResourcePrerequisite(Base):
    __tablename__ = "resource_prerequisites"
    __table_args__ = (
        UniqueConstraint("resource_id", "skill_id", name="uq_resource_prereq_pair"),
        CheckConstraint("min_level >= 0 AND min_level <= 1", name="min_level_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    min_level: Mapped[float] = mapped_column(Float, nullable=False)

    resource: Mapped[LearningResource] = relationship(back_populates="prerequisites")
    skill: Mapped["Skill"] = relationship()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
