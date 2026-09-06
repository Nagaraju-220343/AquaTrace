from sqlalchemy.orm import Session
from app.models.analysis import AnalysisJob
from app.models.detection import DetectionRecord
from app.schemas.detection import DetectionRecordSchema
from typing import List

def update_job_status(db: Session, job_id: str, status: str, message: str = None):
    job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
    if job:
        job.status = status
        if message:
            job.message = message
        db.commit()
        db.refresh(job)
    return job

def save_detections(db: Session, detections: List[DetectionRecordSchema]):
    records = []
    for det in detections:
        record = DetectionRecord(
            object_id=det.object_id,
            analysis_id=det.analysis_id,
            class_name=det.class_name,
            bbox=det.bbox,
            detector_confidence=det.detector_confidence,
            validation_score=det.validation_score,
            final_confidence=det.final_confidence,
            decision=det.decision,
            source_tile_ids=det.source_tile_ids,
            duplicate_count=det.duplicate_count,
            evidence=det.evidence,
            reason=det.reason,
            latitude=det.latitude,
            longitude=det.longitude,
            dimensions_meters=det.dimensions_meters,
            geo_status=det.geo_status,
            uncertainty_meters=det.uncertainty_meters
        )
        records.append(record)
        
    if records:
        db.add_all(records)
        db.commit()
        
    return records
