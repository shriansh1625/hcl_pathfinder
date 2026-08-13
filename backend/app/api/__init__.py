from fastapi import APIRouter

from app.api.assessments import router as assessments_router
from app.api.health import router as health_router
from app.api.learners import router as learners_router
from app.api.paths import router as paths_router
from app.api.roles import router as roles_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(learners_router)
api_router.include_router(roles_router)
api_router.include_router(paths_router)
api_router.include_router(assessments_router)
