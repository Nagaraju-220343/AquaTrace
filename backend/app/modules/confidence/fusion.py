from typing import Dict
from .config import get_weights_for_class

def calculate_final_confidence(class_name: str, detector_conf: float, evidence: Dict[str, float]) -> float:
    """
    Fuses the detector confidence and evidence scores using class-specific weights.
    Returns a score from 0.0 to 100.0.
    """
    weights = get_weights_for_class(class_name)
    
    final_score = 0.0
    
    # Add detector confidence
    if "detector_confidence" in weights:
        final_score += detector_conf * weights["detector_confidence"]
        
    # Add evidence values
    for ev_key, weight in weights.items():
        if ev_key != "detector_confidence":
            val = evidence.get(ev_key, 0.0)
            final_score += val * weight
            
    # Clamp between 0 and 100
    return max(0.0, min(100.0, round(final_score, 2)))
