from typing import Tuple, List
from .config import DECISION_THRESHOLDS

def determine_decision(final_confidence: float, class_name: str, evidence: dict) -> Tuple[str, List[str]]:
    """
    Returns the operational decision (ACCEPT, REVIEW, REJECT) and a list of reasons.
    """
    reasons = []
    
    # 1. Hard filters (e.g., extremely tiny box)
    if "size_score" in evidence and evidence["size_score"] < 0.05:
        return "REJECT", ["Box size is too small (noise)"]
        
    # 2. Confidence thresholds
    if final_confidence >= DECISION_THRESHOLDS["ACCEPT"]:
        decision = "ACCEPT"
    elif final_confidence >= DECISION_THRESHOLDS["REVIEW"]:
        decision = "REVIEW"
        reasons.append("Confidence is marginal, requires human review.")
    else:
        decision = "REJECT"
        reasons.append(f"Confidence {final_confidence} is below REVIEW threshold.")
        
    # 3. Add context to reasons based on class
    if class_name == "crabpot" and evidence.get("specialist_confidence", 1.0) < 0.2:
        reasons.append("Specialist validation score was very low.")
        
    return decision, reasons
