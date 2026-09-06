import pytest
from app.modules.confidence.fusion import calculate_final_confidence
from app.modules.confidence.decision import determine_decision
from app.schemas.detection import DetectionRecordSchema
from app.modules.confidence.pipeline import run_confidence_pipeline

def test_crabpot_fusion():
    # detector_conf = 0.5 (weight 30) = 15
    # specialist_conf = 0.9 (weight 70) = 63
    # Total = 78
    score = calculate_final_confidence("crabpot", 0.5, {"specialist_confidence": 0.9})
    assert score == 78.0

def test_decision_logic():
    # 85 should be ACCEPT
    dec, _ = determine_decision(85.0, "shipwreck", {})
    assert dec == "ACCEPT"
    
    # 60 should be REVIEW
    dec, _ = determine_decision(60.0, "crabpot", {})
    assert dec == "REVIEW"
    
    # 40 should be REJECT
    dec, reasons = determine_decision(40.0, "pipeline", {})
    assert dec == "REJECT"
    assert "below REVIEW threshold" in reasons[0]
    
    # Tiny box should be REJECT regardless of final_confidence
    dec, reasons = determine_decision(90.0, "shipwreck", {"size_score": 0.01})
    assert dec == "REJECT"
    assert "Box size is too small" in reasons[0]

def test_confidence_pipeline():
    det = DetectionRecordSchema(
        object_id="test",
        analysis_id="job",
        class_name="crabpot",
        bbox=[0, 0, 100, 100],
        detector_confidence=0.8,
        evidence={"specialist_confidence": 0.95}
    )
    
    # 0.8 * 30 = 24
    # 0.95 * 70 = 66.5
    # Total = 90.5 -> ACCEPT
    
    updated_dets = run_confidence_pipeline([det])
    
    assert updated_dets[0].final_confidence == 90.5
    assert updated_dets[0].decision == "ACCEPT"
