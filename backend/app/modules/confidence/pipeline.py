from typing import List
from app.schemas.detection import DetectionRecordSchema
from .fusion import calculate_final_confidence
from .decision import determine_decision

def run_confidence_pipeline(detections: List[DetectionRecordSchema]) -> List[DetectionRecordSchema]:
    """
    Fuses evidence and assigns the final decision (ACCEPT, REVIEW, REJECT) for each detection.
    """
    for det in detections:
        # Fuse evidence
        evidence_dict = det.evidence or {}
        
        # We also pass validation_score dynamically if it exists but wasn't in evidence
        if det.validation_score is not None and "specialist_confidence" not in evidence_dict:
            evidence_dict["specialist_confidence"] = det.validation_score
            
        final_conf = calculate_final_confidence(det.class_name, det.detector_confidence, evidence_dict)
        det.final_confidence = final_conf
        
        # Make decision
        decision, reasons = determine_decision(final_conf, det.class_name, evidence_dict)
        det.decision = decision
        det.reason = reasons
        
    return detections
