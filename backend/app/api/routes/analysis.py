from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.models.analysis import AnalysisJob
from app.models.detection import DetectionRecord
from app.db.crud import update_job_status, save_detections
from app.config import settings
import cv2
import os
import uuid
import shutil
import logging
from typing import List, Optional
from app.modules.preprocessing.pipeline import run_preprocessing_pipeline
from app.modules.detection.pipeline import run_detection_pipeline
from app.modules.validation.pipeline import run_validation_pipeline
from app.modules.confidence.pipeline import run_confidence_pipeline
from app.modules.geotagging.pipeline import run_geotagging_pipeline
from app.modules.reporting.reporting import generate_all_reports

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Core Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _run_pipeline_sync(job_id: str, file_path: str, metadata: dict):
    """
    Runs the full 7-step detection pipeline synchronously in a thread pool.
    Creates its own DB session (request-scoped sessions expire after HTTP response).

    Steps:
        1. Ingestion (image load + validation)
        2. Preprocessing (quality check, motion artifact detection, Lee speckle filter)
        3. YOLO Detection
        4. Validation (lightweight image checks + specialist for crabpots)
        5. Confidence Scoring (deterministic evidence fusion)
        6. Geo-tagging (GPS + altitude → lat/lon + bounding dimensions)
        7. Persistence + Report Generation
    """
    db = SessionLocal()
    try:
        update_job_status(db, job_id, "PROCESSING")

        # 1. Ingestion
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError(f"Could not read image at: {file_path}")
        logger.info(f"[{job_id}] Image loaded: {img.shape}")

        # 2. Preprocessing (includes motion detection + speckle filter)
        processed_images, pipeline_metadata = run_preprocessing_pipeline(img)
        motion_report = pipeline_metadata.get("motion_report", {})
        motion_score = motion_report.get("motion_quality_score", 1.0)
        artifact_types = motion_report.get("artifact_types", [])
        logger.info(f"[{job_id}] Preprocessing done. Motion score: {motion_score:.2f}, artifacts: {artifact_types}")

        # 3. Detection
        detections = run_detection_pipeline(processed_images, pipeline_metadata, job_id)
        logger.info(f"[{job_id}] Detection: {len(detections)} candidates")

        # 4. Validation
        detections = run_validation_pipeline(detections, img)

        # 5. Confidence scoring — inject motion quality penalty into evidence
        for det in detections:
            ev = det.evidence or {}
            ev["motion_quality_score"] = motion_score
            det.evidence = ev
        detections = run_confidence_pipeline(detections)
        logger.info(f"[{job_id}] Confidence done: {[(d.class_name, d.decision, round(d.final_confidence or 0, 1)) for d in detections]}")

        # 6. Geo-tagging
        detections = run_geotagging_pipeline(detections, metadata or {})

        # 7. Persistence
        save_detections(db, detections)
        logger.info(f"[{job_id}] Saved {len(detections)} detections to DB.")

        # 8. Report generation (JSON + CSV)
        generate_all_reports(job_id, detections)

        # Build completion message
        motion_note = ""
        if artifact_types:
            motion_note = f" | Motion artifacts: {', '.join(artifact_types)}"
        update_job_status(
            db, job_id, "COMPLETED",
            message=f"Pipeline finished. {len(detections)} detections saved.{motion_note}"
        )
        return {
            "detection_count": len(detections),
            "motion_quality_score": motion_score,
            "artifact_types": artifact_types,
            "speckle_filter": pipeline_metadata.get("speckle_method", "lee"),
            "nadir_info": motion_report.get("nadir_info", {}),
            "dropout_bands_count": len(motion_report.get("dropout_bands", [])),
            "decisions": {d.decision or "UNKNOWN": 1 for d in detections},
        }

    except Exception as e:
        logger.error(f"[{job_id}] Pipeline failed: {e}", exc_info=True)
        try:
            update_job_status(db, job_id, "FAILED", message=str(e))
        except Exception:
            pass
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Single Analysis Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class JobMetadata(BaseModel):
    sensor_type: Optional[str] = None
    altitude_m: Optional[float] = None
    speed_knots: Optional[float] = None
    gps_start_lat: Optional[float] = None
    gps_start_lon: Optional[float] = None

@router.post("/analysis/run")
async def run_analysis(file_path: str, metadata: Optional[JobMetadata] = None, db: Session = Depends(get_db)):
    """
    Trigger the full anomaly detection pipeline for a single uploaded image.
    Runs synchronously in a thread pool (fresh DB session inside).
    """
    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"

    new_job = AnalysisJob(job_id=job_id, status="PENDING", input_file_path=file_path)
    db.add(new_job)
    db.commit()

    pipeline_report = {}
    try:
        meta_dict = metadata.dict() if metadata else {}
        pipeline_report = await run_in_threadpool(_run_pipeline_sync, job_id, file_path, meta_dict)
    except Exception:
        pass  # Status already set to FAILED inside _run_pipeline_sync

    # Refresh to get the final status
    db.refresh(new_job)
    return {
        "job_id": job_id,
        "status": new_job.status,
        "message": new_job.message,
        "image_url": f"/uploads/{os.path.basename(file_path)}",
        "pipeline_report": pipeline_report or {}
    }


@router.get("/analysis/status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    filename = os.path.basename(job.input_file_path) if job.input_file_path else None
    return {
        "job_id": job.job_id,
        "status": job.status,
        "message": job.message,
        "image_url": f"/uploads/{filename}" if filename else None
    }


@router.get("/analysis/jobs")
async def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(AnalysisJob).order_by(AnalysisJob.created_at.desc()).all()
    return [
        {
            "job_id": j.job_id,
            "status": j.status,
            "input_file_path": j.input_file_path,
            "image_url": f"/uploads/{os.path.basename(j.input_file_path)}" if j.input_file_path else None,
            "message": j.message,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


@router.get("/analysis/image/{job_id}")
async def get_job_image(job_id: str, db: Session = Depends(get_db)):
    """
    Returns the sonar image for a given job as a file download.
    Clients can also use the image_url field directly from /analysis/jobs or /analysis/status.
    """
    job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
    if not job or not job.input_file_path:
        raise HTTPException(status_code=404, detail="Job or image not found")
    if not os.path.exists(job.input_file_path):
        raise HTTPException(status_code=404, detail="Image file not found on disk")
    return FileResponse(job.input_file_path, media_type="image/png")


@router.get("/analysis/detections/{job_id}")
async def get_detections(job_id: str, db: Session = Depends(get_db)):
    records = db.query(DetectionRecord).filter(DetectionRecord.analysis_id == job_id).all()
    return [
        {
            "object_id": r.object_id,
            "class_name": r.class_name,
            "bbox": r.bbox,
            "detector_confidence": r.detector_confidence,
            "final_confidence": r.final_confidence,
            "decision": r.decision,
            "validation_score": r.validation_score,
            "geo_status": r.geo_status,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "dimensions_meters": r.dimensions_meters,
            "reason": r.reason,
            "evidence": r.evidence,
        }
        for r in records
    ]


@router.get("/analysis/all_detections")
async def get_all_detections(db: Session = Depends(get_db)):
    """
    Returns all detections across all jobs that have a valid geotag (latitude/longitude are not null).
    """
    records = db.query(DetectionRecord).filter(
        DetectionRecord.latitude.isnot(None),
        DetectionRecord.longitude.isnot(None)
    ).all()
    
    return [
        {
            "object_id": r.object_id,
            "job_id": r.analysis_id,
            "class_name": r.class_name,
            "final_confidence": r.final_confidence,
            "decision": r.decision,
            "geo_status": r.geo_status,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "dimensions_meters": r.dimensions_meters,
            "image_url": f"/api/v1/analysis/image/{r.analysis_id}"
        }
        for r in records
    ]

@router.get("/analysis/report/{job_id}/{fmt}")
async def download_report(job_id: str, fmt: str, db: Session = Depends(get_db)):
    if fmt not in ["json", "csv", "pdf"]:
        raise HTTPException(status_code=400, detail="Format must be json, csv, or pdf")
    report_path = os.path.join("reports", f"{job_id}_report.{fmt}")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"Report not found for job {job_id}")
    media_types = {"json": "application/json", "csv": "text/csv", "pdf": "application/pdf"}
    return FileResponse(report_path, media_type=media_types[fmt], filename=f"{job_id}_report.{fmt}")


# ─────────────────────────────────────────────────────────────────────────────
# Batch Processing Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/analysis/batch")
async def run_batch_analysis(
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Batch upload and process multiple sonar images.
    Creates one job per image and processes them sequentially.
    Returns a batch_id and list of individual job IDs.

    Usage: POST /api/v1/analysis/batch with multiple 'images' files.
    """
    batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
    job_ids = []

    os.makedirs(settings.upload_dir, exist_ok=True)

    for image_file in images:
        # Save file
        file_ext = os.path.splitext(image_file.filename)[1] or ".png"
        unique_name = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.upload_dir, unique_name)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(image_file.file, f)

        # Create job record
        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        new_job = AnalysisJob(
            job_id=job_id,
            status="PENDING",
            input_file_path=file_path
        )
        db.add(new_job)
        db.commit()
        job_ids.append(job_id)

    # Run all jobs sequentially in the thread pool
    async def _run_all():
        for jid, jpath in zip(job_ids, [os.path.join(settings.upload_dir, f) for f in os.listdir(settings.upload_dir)]):
            try:
                await run_in_threadpool(_run_pipeline_sync, jid, jpath, {})
            except Exception:
                pass

    # Fire-and-forget: process in background
    import asyncio
    asyncio.create_task(_run_all())

    return {
        "batch_id": batch_id,
        "total_jobs": len(job_ids),
        "job_ids": job_ids,
        "message": f"Batch of {len(job_ids)} images submitted. Poll individual job statuses."
    }
