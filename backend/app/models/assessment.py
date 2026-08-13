from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Assessment(TimestampMixin, Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "pass_threshold >= 0 AND pass_threshold <= 1",
            name="pass_threshold_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    primary_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False
    )
    pass_threshold: Mapped[float] = mapped_column(Float, nullable=False)

    questions: Mapped[list[AssessmentQuestion]] = relationship(
        back_populates="assessment"
    )
    primary_skill: Mapped["Skill"] = relationship()


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    __table_args__ = (
        UniqueConstraint("assessment_id", "position", name="uq_question_position"),
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="q_difficulty_range"),
        CheckConstraint("correct_index >= 0", name="correct_index_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False
    )
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    choices: Mapped[list] = mapped_column(JSONB, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    concept_tag: Mapped[str] = mapped_column(String(80), nullable=False)

    assessment: Mapped[Assessment] = relationship(back_populates="questions")
    skill: Mapped["Skill"] = relationship()
