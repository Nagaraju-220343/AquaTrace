from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.analysis import AnalysisJobRead
from app.modules.ingestion.pipeline import run_ingestion
from app.config import settings

router = APIRouter()

@router.post("/upload", response_model=AnalysisJobRead)
def upload_file(
    image: UploadFile = File(...),
    metadata: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        job = run_ingestion(db, image, metadata, settings.upload_dir)
        return job
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
