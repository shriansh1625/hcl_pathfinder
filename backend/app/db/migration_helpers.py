"""Idempotent helpers for Alembic migrations (safe on Render restarts)."""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


def has_table(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def has_column(table: str, column: str) -> bool:
    return any(col["name"] == column for col in inspect(op.get_bind()).get_columns(table))


def has_index(table: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspect(op.get_bind()).get_indexes(table))
