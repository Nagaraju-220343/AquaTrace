import numpy as np
from typing import List
from app.schemas.detection import DetectionRecordSchema
from app.modules.validation.cropper import extract_contextual_crop
from app.modules.validation.lightweight_checks import run_lightweight_checks
from app.modules.validation.crabpot_validator import validate_crabpot

def run_validation_pipeline(detections: List[DetectionRecordSchema], raw_image: np.ndarray) -> List[DetectionRecordSchema]:
    """
    Validates candidates. Updates the DetectionRecordSchema in-place or returns updated copies.
    """
    for det in detections:
        # Extract contextual crop
        crop, local_bbox = extract_contextual_crop(raw_image, det.bbox, padding_percent=0.25)
        
        # Base lightweight checks for everyone
        evidence = run_lightweight_checks(crop, local_bbox, det.bbox)
        
        # If it's a crabpot, run the specialist
        if det.class_name == "crabpot":
            crabpot_evidence = validate_crabpot(crop)
            evidence.update(crabpot_evidence)
            det.validation_score = crabpot_evidence["validation_score"]
        else:
            det.validation_score = evidence["validation_score"]
            
        det.evidence = evidence
        
    return detections
