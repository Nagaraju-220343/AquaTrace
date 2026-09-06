import os
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    app_name: str = "Marine Anomaly Detection API"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = f"sqlite:///{BASE_DIR}/database/marine_detection.db"
    models_dir: str = str(BASE_DIR / "models")
    upload_dir: str = str(BASE_DIR / "data/uploads")
    processed_dir: str = str(BASE_DIR / "data/processed")
    reports_dir: str = str(BASE_DIR / "reports")
    
    class Config:
        env_file = ".env"

settings = Settings()
