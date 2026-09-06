import numpy as np
import cv2
from typing import Tuple

def check_image_quality(image: np.ndarray) -> Tuple[bool, str, dict]:
    """
    Validates if the image has sufficient quality/contrast for detection.
    Returns (is_valid, error_message, quality_metrics).
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    std_dev = np.std(gray)
    mean_val = np.mean(gray)
    
    metrics = {
        "mean_intensity": float(mean_val),
        "std_deviation": float(std_dev)
    }
    
    # If the standard deviation is extremely low, the image is likely a solid color
    if std_dev < 2.0:
        return False, "Image has virtually no contrast (solid color).", metrics
        
    return True, "", metrics
