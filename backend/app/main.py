from fastapi import FastAPI

from app.api import api_router

app = FastAPI(
    title="PathFinder API",
    description="Adaptive Career Path Intelligence — Slice 2 personalized paths.",
    version="0.2.0",
)
app.include_router(api_router)
