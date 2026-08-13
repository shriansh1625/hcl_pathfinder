"""Slice 3.2: one ACTIVE path constraint + assessment definition hash.

Revision ID: 0004_slice32_hardening
Revises: 0003_assessment_adaptation
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_slice32_hardening"
down_revision: Union[str, Sequence[str], None] = "0003_assessment_adaptation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("definition_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "uq_learning_paths_user_role_active",
        "learning_paths",
        ["user_id", "role_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index("uq_learning_paths_user_role_active", table_name="learning_paths")
    op.drop_column("assessments", "definition_hash")
