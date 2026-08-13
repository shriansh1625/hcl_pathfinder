from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[Profile | None] = relationship(back_populates="user", uselist=False)
    evidence: Mapped[list[SkillEvidence]] = relationship(back_populates="user")
    skills: Mapped[list[UserSkill]] = relationship(back_populates="user")
    paths: Mapped[list["LearningPath"]] = relationship(
        "LearningPath", back_populates="user"
    )


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    target_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    experience_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    weekly_hours: Mapped[int | None] = mapped_column(nullable=True)
    learning_style: Mapped[str | None] = mapped_column(String(40), nullable=True)
    timeline_weeks: Mapped[int | None] = mapped_column(nullable=True)
    interests: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
    target_role: Mapped["Role | None"] = relationship()


class SkillEvidence(Base):
    """Append-only. Never update a row; insert a new observation."""

    __tablename__ = "skill_evidence"
    __table_args__ = (
        CheckConstraint(
            "observed_level >= 0 AND observed_level <= 1",
            name="observed_level_range",
        ),
        CheckConstraint(
            "reliability >= 0 AND reliability <= 1",
            name="reliability_range",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="evidence_confidence_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_level: Mapped[float] = mapped_column(Float, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="evidence")
    skill: Mapped["Skill"] = relationship()


class UserSkill(Base):
    """Fused learner state. proficiency is NULL when status is UNKNOWN."""

    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skills_pair"),
        CheckConstraint(
            "proficiency IS NULL OR (proficiency >= 0 AND proficiency <= 1)",
            name="proficiency_range_or_null",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="user_skill_confidence_range",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    evidence_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship()
