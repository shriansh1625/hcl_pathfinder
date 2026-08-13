from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.intelligence import CompetencyRead, RoleCompetencyRead
from app.services.profiling.repository import load_role_competencies

router = APIRouter(prefix="/v1")


@router.get("/roles/{role_slug}/competencies", response_model=RoleCompetencyRead)
def role_competencies(role_slug: str, session: Session = Depends(get_session)) -> RoleCompetencyRead:
    try:
        role = load_role_competencies(session, role_slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
