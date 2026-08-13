from fastapi import FastAPI

from app.api import api_router

app = FastAPI(
    title="PathFinder API",
    description="Adaptive Career Path Intelligence — Slice 0 foundation only.",
    version="0.1.0",
)
app.include_router(api_router)
