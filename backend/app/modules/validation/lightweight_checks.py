import numpy as np
import cv2
from typing import List, Dict

def run_lightweight_checks(crop: np.ndarray, local_bbox: List[int], original_bbox: List[int]) -> Dict[str, float]:
    """
    Performs lightweight image-processing checks for non-crabpot classes.
    Returns an evidence dictionary.
    """
    x1, y1, x2, y2 = local_bbox
    box_w = x2 - x1
    box_h = y2 - y1
    
    # 1. Bounding box validity & size
    # If the box is extremely small (e.g. < 5x5), score is low
    size_score = min(1.0, (box_w * box_h) / 2500.0) # 50x50 is max score
    
    # 2. Contrast with surrounding background
    if len(crop.shape) == 3:
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray_crop = crop
        
    mask = np.zeros_like(gray_crop, dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255
    
    bg_mask = cv2.bitwise_not(mask)
    
    # Calculate means
    fg_mean = cv2.mean(gray_crop, mask=mask)[0]
    bg_mean = cv2.mean(gray_crop, mask=bg_mask)[0]
    
    contrast_diff = abs(fg_mean - bg_mean)
    contrast_score = min(1.0, contrast_diff / 100.0)
    
    # 3. Texture / Edge strength (Laplacian variance)
    fg_crop = gray_crop[y1:y2, x1:x2]
    if fg_crop.size > 0:
        laplacian = cv2.Laplacian(fg_crop, cv2.CV_64F)
        edge_variance = laplacian.var()
        texture_score = min(1.0, edge_variance / 500.0)
    else:
        texture_score = 0.0
        
    # Aggregate to a generic validation score
    # This is a very basic fusion; Module 5 handles the true fusion later.
    overall_score = (size_score + contrast_score + texture_score) / 3.0
    
    return {
        "size_score": round(size_score, 3),
        "contrast_score": round(contrast_score, 3),
        "texture_score": round(texture_score, 3),
        "validation_score": round(overall_score, 3)
    }
