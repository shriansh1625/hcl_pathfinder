"""Slice 3: assessment attempts + adaptation audit columns.

Revision ID: 0003_assessment_adaptation
Revises: 0002_nullable_confidence
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0003_assessment_adaptation"
down_revision: Union[str, Sequence[str], None] = "0002_nullable_confidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column(
            "target_role_id",
            UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "assessments",
        sa.Column("target_skills", JSONB, nullable=True),
    )

    op.create_table(
        "assessment_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("answers", JSONB, nullable=False),
        sa.Column("result", JSONB, nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "user_id",
            "attempt_number",
            name="uq_attempt_assessment_user_number",
        ),
        sa.CheckConstraint("attempt_number >= 1", name="attempt_number_positive"),
    )

    op.add_column(
        "adaptation_events",
        sa.Column("trigger_type", sa.String(40), nullable=True),
    )
    op.add_column(
        "adaptation_events",
        sa.Column("changed_skills", JSONB, nullable=True),
    )
    op.add_column(
        "adaptation_events",
        sa.Column("changes", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("adaptation_events", "changes")
    op.drop_column("adaptation_events", "changed_skills")
    op.drop_column("adaptation_events", "trigger_type")
    op.drop_table("assessment_attempts")
    op.drop_column("assessments", "target_skills")
    op.drop_column("assessments", "target_role_id")
