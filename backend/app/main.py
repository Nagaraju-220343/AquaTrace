# AquaTrace — Main Application Entry Point (reload: v2)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.router import api_router
from app.config import settings
from app.db.database import engine, Base
from app.models.analysis import AnalysisJob
from app.models.sonar_file import SonarFile
from app.models.detection import DetectionRecord
import os

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="AquaTrace API",
    version="1.0.0"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For V1, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Serve uploaded images for frontend overlay display
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
