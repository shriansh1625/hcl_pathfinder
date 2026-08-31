"""Ensure PostgreSQL is migrated and seeded for local / first-run startup."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.seed import seed_ontology
from app.db.session import SessionLocal, engine
from app.models import Role

logger = logging.getLogger(__name__)


def database_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def ensure_database_ready() -> bool:
    """Seed when Postgres is reachable and the ontology tables are empty."""
    if not database_available():
        logger.warning(
            "PostgreSQL is not reachable at DATABASE_URL. "
            "Read-only ontology endpoints will still work; run "
            "`docker compose up -d` and `python scripts/seed.py` for full learner/path flows."
        )
        return False

    session = SessionLocal()
    try:
        role_count = session.scalar(select(func.count()).select_from(Role)) or 0
        if role_count == 0:
            logger.info("Empty database detected — seeding ontology from YAML.")
            seed_ontology(session)
            session.commit()
            logger.info("Ontology seed complete.")
        return True
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Database bootstrap failed: %s", exc)
        return False
    finally:
        session.close()
