from fastapi import APIRouter
from app.api.routes import health, files, analysis

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(files.router, tags=["files"])
api_router.include_router(analysis.router, tags=["analysis"])
