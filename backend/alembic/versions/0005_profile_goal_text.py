"""Add nullable goal_text to learner profiles.

Revision ID: 0005_profile_goal_text
Revises: 0004_slice32_hardening
Create Date: 2026-08-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_profile_goal_text"
down_revision: Union[str, Sequence[str], None] = "0004_slice32_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("goal_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "goal_text")