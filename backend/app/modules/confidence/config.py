from typing import Dict

# Thresholds mapped to 0-100 scale.
# Note: Sonar YOLO models trained on small datasets produce low raw confidence (0.01-0.08).
# We lower thresholds so weak-but-valid detections are retained for human review.
DECISION_THRESHOLDS = {
    "ACCEPT": 60.0,
    "REVIEW": 5.0   # Anything below REVIEW is REJECT
}

# Additive fusion weights per class.
# The weights should roughly sum to 100 if all inputs are perfectly 1.0
FUSION_CONFIG = {
    "crabpot": {
        "detector_confidence": 30.0,
        "specialist_confidence": 70.0 # Heavily weighted additive score
    },
    "default": {
        "detector_confidence": 60.0,  # Higher weight since sonar models have low raw conf
        "size_score": 10.0,
        "contrast_score": 15.0,
        "texture_score": 15.0
    }
}

def get_weights_for_class(class_name: str) -> Dict[str, float]:
    return FUSION_CONFIG.get(class_name, FUSION_CONFIG["default"])
