import uuid
import os
from sqlalchemy.orm import Session
from fastapi import UploadFile
from typing import Optional

from app.models.analysis import AnalysisJob
from app.models.sonar_file import SonarFile
from app.modules.ingestion.loader import load_and_validate_image
from app.modules.ingestion.metadata_parser import parse_metadata

def run_ingestion(db: Session, image: UploadFile, metadata: Optional[UploadFile], upload_dir: str):
    # 1. Image validation and loading
    is_valid, img_path, err = load_and_validate_image(image, upload_dir)
    if not is_valid:
        raise ValueError(f"Image validation failed: {err}")

    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
    file_id = f"FILE-{uuid.uuid4().hex[:8].upper()}"

    # 2. Metadata parsing
    parsed_meta = {}
    meta_path = None
    if metadata:
        meta_bytes = metadata.file.read()
        parsed_meta = parse_metadata(meta_bytes, metadata.filename) or {}
        
        # Save raw metadata file
        meta_path = os.path.join(upload_dir, f"{job_id}_{metadata.filename}")
        with open(meta_path, "wb") as f:
            f.write(meta_bytes)

    # 3. Job creation
    job = AnalysisJob(job_id=job_id, status="PENDING", input_file_path=img_path)
    
    # 4. Sonar file record
    sonar_file = SonarFile(
        id=file_id,
        analysis_id=job_id,
        original_filename=image.filename,
        file_path=img_path,
        metadata_path=meta_path,
        ping_id=parsed_meta.get("ping_id"),
        timestamp=parsed_meta.get("timestamp"),
        range_m=parsed_meta.get("range_m"),
        side=parsed_meta.get("side"),
        latitude=parsed_meta.get("latitude"),
        longitude=parsed_meta.get("longitude"),
        heading=parsed_meta.get("heading")
    )

    db.add(job)
    db.add(sonar_file)
    db.commit()
    db.refresh(job)
    
    # Send to preprocessing (Stub for now, or handled by orchestrator)
    # The orchestrator will pick this up from the pending status
    
    return job
