import numpy as np
from typing import List, Tuple

def extract_contextual_crop(image: np.ndarray, bbox: List[int], padding_percent: float = 0.25) -> Tuple[np.ndarray, List[int]]:
    """
    Extracts a crop of the bounding box with extra context padding.
    Padding is a percentage of the box's width and height.
    Returns the cropped image and the new bounding box coordinates relative to the crop.
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    
    box_w = x2 - x1
    box_h = y2 - y1
    
    pad_w = int(box_w * padding_percent)
    pad_h = int(box_h * padding_percent)
    
    # Calculate expanded crop boundaries (clamped to image size)
    crop_x1 = max(0, x1 - pad_w)
    crop_y1 = max(0, y1 - pad_h)
    crop_x2 = min(w, x2 + pad_w)
    crop_y2 = min(h, y2 + pad_h)
    
    crop = image[crop_y1:crop_y2, crop_x1:crop_x2].copy()
    
    # Calculate object's new coordinates relative to the crop
    new_x1 = x1 - crop_x1
    new_y1 = y1 - crop_y1
    new_x2 = x2 - crop_x1
    new_y2 = y2 - crop_y1
    
    return crop, [new_x1, new_y1, new_x2, new_y2]
