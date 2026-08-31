from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import Role
from app.schemas import RoleRead
from app.schemas.intelligence import CompetencyRead, DemoEvidenceRead, RoleCompetencyRead, RoleDetailRead
from app.services.demo.evidence import load_demo_evidence
from app.services.ontology.roles import (
    list_roles_from_ontology,
    role_competencies_from_ontology,
    role_detail_from_ontology,
)
from app.services.profiling.repository import load_role_competencies

router = APIRouter(prefix="/v1")


def _db_roles(session: Session) -> list[Role]:
    return list(session.scalars(select(Role).order_by(Role.name)).all())


@router.get("/roles", response_model=list[RoleRead])
def list_roles(session: Session = Depends(get_session)) -> list[RoleRead]:
    try:
        rows = _db_roles(session)
        if rows:
            return rows
    except SQLAlchemyError:
        session.rollback()
    return list_roles_from_ontology()


@router.get("/roles/{role_slug}/competencies", response_model=RoleCompetencyRead)
def role_competencies(role_slug: str, session: Session = Depends(get_session)) -> RoleCompetencyRead:
    try:
        role = load_role_competencies(session, role_slug)
        return RoleCompetencyRead(
            role=role.role_slug,
            name=role.role_name,
            competencies=[
                CompetencyRead(
                    skill=item.skill_slug,
                    name=item.skill_name,
                    target_level=item.target_level,
                    importance=item.importance,
                    required_status=item.required_status.value,
                )
                for item in role.competencies
            ],
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError:
        session.rollback()
        try:
            return role_competencies_from_ontology(role_slug)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/roles/{role_slug}/detail", response_model=RoleDetailRead)
def role_detail(role_slug: str, session: Session = Depends(get_session)) -> RoleDetailRead:
    try:
        row = session.scalar(select(Role).where(Role.slug == role_slug))
        if row is None:
            raise KeyError(f"Unknown role: {role_slug}")
        role = load_role_competencies(session, role_slug)
        core = [item.skill_slug for item in role.competencies if item.required_status.value == "CORE"][:8]
        categories = sorted({item.skill_name.split()[0] for item in role.competencies[:6]})
        return RoleDetailRead(
            slug=row.slug,
            name=row.name,
            description=row.description,
            competency_count=len(role.competencies),
            core_skills=core,
            focus_areas=categories,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError:
        session.rollback()
        try:
            return role_detail_from_ontology(role_slug)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/roles/{role_slug}/demo-evidence", response_model=list[DemoEvidenceRead])
def role_demo_evidence(role_slug: str, session: Session = Depends(get_session)) -> list[DemoEvidenceRead]:
    known = False
    try:
        row = session.scalar(select(Role).where(Role.slug == role_slug))
        known = row is not None
    except SQLAlchemyError:
        session.rollback()
        known = any(item.slug == role_slug for item in list_roles_from_ontology())

    if not known:
        raise HTTPException(status_code=404, detail=f"Unknown role: {role_slug}")
    return [DemoEvidenceRead(**item) for item in load_demo_evidence(role_slug)]
