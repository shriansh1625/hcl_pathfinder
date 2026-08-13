"""Allow UNKNOWN fused skills to store NULL confidence.

Revision ID: 0002_nullable_confidence
Revises: 0001_initial
Create Date: 2026-08-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_nullable_confidence"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "user_skills",
        "confidence",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE user_skills SET confidence = 0 WHERE confidence IS NULL")
    op.alter_column(
        "user_skills",
        "confidence",
        existing_type=sa.Float(),
        nullable=False,
    )
