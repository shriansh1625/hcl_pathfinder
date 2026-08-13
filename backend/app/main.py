from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.ontology.load import load_ontology


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_ontology()
    yield


app = FastAPI(
    title="PathFinder API",
    description="Adaptive Career Path Intelligence — Slice 2 personalized paths.",
    version="0.2.0",
    lifespan=lifespan,
)
app.include_router(api_router)
