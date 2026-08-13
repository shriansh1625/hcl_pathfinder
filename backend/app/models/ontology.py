from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RelationshipType, RequiredStatus
from app.db.base import Base, TimestampMixin


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)

    outgoing_relationships: Mapped[list[SkillRelationship]] = relationship(
        back_populates="source_skill",
        foreign_keys="SkillRelationship.source_skill_id",
    )
    incoming_relationships: Mapped[list[SkillRelationship]] = relationship(
        back_populates="target_skill",
        foreign_keys="SkillRelationship.target_skill_id",
    )


class SkillRelationship(Base):
    __tablename__ = "skill_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_skill_id",
            "target_skill_id",
            "relationship_type",
            name="uq_skill_relationships_edge",
        ),
        CheckConstraint("source_skill_id <> target_skill_id", name="no_self_reference"),
        CheckConstraint("strength >= 0 AND strength <= 1", name="strength_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    source_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    target_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source_skill: Mapped[Skill] = relationship(
        back_populates="outgoing_relationships", foreign_keys=[source_skill_id]
    )
    target_skill: Mapped[Skill] = relationship(
        back_populates="incoming_relationships", foreign_keys=[target_skill_id]
    )

    @property
    def kind(self) -> RelationshipType:
        return RelationshipType(self.relationship_type)


class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    role_skills: Mapped[list[RoleSkill]] = relationship(back_populates="role")


class RoleSkill(Base):
    __tablename__ = "role_skills"
    __table_args__ = (
        UniqueConstraint("role_id", "skill_id", name="uq_role_skills_pair"),
        CheckConstraint("target_level >= 0 AND target_level <= 1", name="target_level_range"),
        CheckConstraint("importance >= 0 AND importance <= 1", name="importance_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    target_level: Mapped[float] = mapped_column(Float, nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False)
    required_status: Mapped[str] = mapped_column(String(32), nullable=False)

    role: Mapped[Role] = relationship(back_populates="role_skills")
    skill: Mapped[Skill] = relationship()

    @property
    def required(self) -> RequiredStatus:
        return RequiredStatus(self.required_status)
