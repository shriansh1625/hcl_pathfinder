from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.db.bootstrap import ensure_database_ready
from app.ontology.load import load_ontology

logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_ontology()

    async def _bootstrap() -> None:
        ready = await asyncio.to_thread(ensure_database_ready)
        if ready:
            logger.info("Database ready.")

    asyncio.create_task(_bootstrap())
    yield


app = FastAPI(
    title="PathFinder API",
    description="Adaptive Career Path Intelligence — Slice 5 grounded explanations.",
    version="0.5.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
