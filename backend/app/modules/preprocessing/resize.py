import numpy as np
import cv2
from typing import Tuple

def letterbox_resize(image: np.ndarray, target_size: int = 640) -> Tuple[np.ndarray, dict]:
    """
    Resizes image to target_size x target_size while preserving aspect ratio by adding padding.
    Returns the resized image and a transform dictionary required to reverse the bounding boxes later.
    """
    h, w = image.shape[:2]
    
    # Scale ratio (new / old)
    r = min(target_size / h, target_size / w)
    
    # Compute new unpadded dimensions
    new_unpad_h = int(round(h * r))
    new_unpad_w = int(round(w * r))
    
    # Compute padding
    dh = target_size - new_unpad_h
    dw = target_size - new_unpad_w
    
    # Divide padding by 2 to center the image
    dh /= 2
    dw /= 2
    
    # Resize if needed
    if (h, w) != (new_unpad_h, new_unpad_w):
        resized = cv2.resize(image, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)
    else:
        resized = image.copy()
        
    # Add borders (padding)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    
    # Use standard YOLO gray padding (114)
    color = (114, 114, 114) if len(image.shape) == 3 else 114
    
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    
    # transform_info used for reversing boxes to original pixels
    transform_info = {
        "original_w": w,
        "original_h": h,
        "scale_r": r,
        "pad_w": left,
        "pad_h": top
    }
    
    return padded, transform_info
