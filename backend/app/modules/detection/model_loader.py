from ultralytics import YOLO
from typing import Optional
import os
from app.config import settings

_model_cache: Optional[YOLO] = None

def get_yolo_model(model_path: str = None) -> YOLO:
    if model_path is None:
        model_path = os.path.join(settings.models_dir, "best.pt")
        
    global _model_cache
    if _model_cache is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        _model_cache = YOLO(model_path)
    return _model_cache
