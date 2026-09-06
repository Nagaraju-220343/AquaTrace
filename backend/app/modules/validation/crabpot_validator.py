import os
from typing import Optional, Dict
from ultralytics import YOLO
import numpy as np
import logging
from app.config import settings

_crabpot_model_cache: Optional[YOLO] = None
logger = logging.getLogger(__name__)

def get_crabpot_model(model_path: str = None) -> YOLO:
    if model_path is None:
        model_path = os.path.join(settings.models_dir, "gv-yolo26", "model.safetensors")
    
    global _crabpot_model_cache
    if _crabpot_model_cache is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Crabpot specialist model not found at {model_path}")
        # Ultralytics supports loading ONNX natively (it determines task automatically, 
        # or defaults to detect. It detects crab-pot)
        _crabpot_model_cache = YOLO(model_path, task='detect')
    return _crabpot_model_cache

def validate_crabpot(crop: np.ndarray) -> Dict[str, float]:
    """
    Runs the specialist crabpot ONNX model on the image crop.
    Returns the validation score.
    """
    try:
        model = get_crabpot_model()
        results = model.predict(source=crop, verbose=False)
        
        best_conf = 0.0
        
        # In a cropped image, we expect to see at least one detection of the crabpot
        for r in results:
            for box in r.boxes:
                # Assuming class 0 is crabpot as per class_names.txt
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    
        return {
            "specialist_confidence": round(best_conf, 3),
            "validation_score": round(best_conf, 3) # Use the best confidence as the validation score
        }
    except Exception as e:
        logger.error(f"Error running crabpot validation: {e}")
        return {
            "specialist_confidence": 0.0,
            "validation_score": 0.0
        }
