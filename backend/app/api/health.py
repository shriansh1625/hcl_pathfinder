from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.enums import RelationshipType
from app.db.session import get_session
from app.models import Assessment, AssessmentQuestion, LearningResource, Role, Skill, SkillRelationship
from app.ontology.load import load_ontology
from app.schemas import HealthResponse, OntologyStats, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="pathfinder-api", slice="2")


@router.get("/ready", response_model=ReadyResponse)
def ready(session: Session = Depends(get_session)) -> ReadyResponse:
    session.execute(text("SELECT 1"))
    return ReadyResponse(status="ok", database="up")


@router.get("/v1/meta/ontology", response_model=OntologyStats)
def ontology_stats(session: Session = Depends(get_session)) -> OntologyStats:
    hard = session.scalar(
        select(func.count()).select_from(SkillRelationship).where(
            SkillRelationship.relationship_type == RelationshipType.HARD_PREREQUISITE.value
        )
    )
    soft = session.scalar(
        select(func.count()).select_from(SkillRelationship).where(
            SkillRelationship.relationship_type == RelationshipType.SOFT_PREREQUISITE.value
        )
    )
    related = session.scalar(
        select(func.count()).select_from(SkillRelationship).where(
            SkillRelationship.relationship_type == RelationshipType.RELATED.value
        )
    )
    canonical_assessment_slugs = {item.slug for item in load_ontology().assessments}
    resources_total = session.scalar(select(func.count()).select_from(LearningResource)) or 0
    resources_active = (
        session.scalar(
            select(func.count()).select_from(LearningResource).where(LearningResource.is_active.is_(True))
        )
        or 0
    )
    assessments_total = session.scalar(select(func.count()).select_from(Assessment)) or 0
    assessments_canonical = (
        session.scalar(
            select(func.count()).select_from(Assessment).where(Assessment.slug.in_(canonical_assessment_slugs))
        )
        if canonical_assessment_slugs
        else 0
    )
    return OntologyStats(
        skills=session.scalar(select(func.count()).select_from(Skill)) or 0,
        roles=session.scalar(select(func.count()).select_from(Role)) or 0,
        skill_relationships=session.scalar(select(func.count()).select_from(SkillRelationship)) or 0,
        hard_prerequisites=hard or 0,
        soft_prerequisites=soft or 0,
        related=related or 0,
        resources=resources_active,
        resources_total=resources_total,
        assessments=assessments_canonical,
        assessments_total=assessments_total,
        questions=session.scalar(select(func.count()).select_from(AssessmentQuestion)) or 0,
    )
