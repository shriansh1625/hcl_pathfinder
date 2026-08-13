from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.ontology.load import load_ontology


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_ontology()
    yield


app = FastAPI(
    title="PathFinder API",
    description="Adaptive Career Path Intelligence — Slice 4 product experience.",
    version="0.4.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
