import numpy as np
import cv2

def apply_percentile_normalization(image: np.ndarray, lower_p=1.0, upper_p=99.0) -> np.ndarray:
    """
    Applies mild percentile normalization.
    Stretches the intensity so that lower_p becomes 0 and upper_p becomes 255.
    Preserves acoustic shadows by not clipping excessively.
    """
    # Ensure float for calculations
    img_float = image.astype(np.float32)
    
    # Calculate percentiles
    p_low = np.percentile(img_float, lower_p)
    p_high = np.percentile(img_float, upper_p)
    
    # Avoid division by zero if the image is completely flat
    if p_high - p_low < 1e-5:
        return image.copy()
        
    # Stretch
    normalized = (img_float - p_low) / (p_high - p_low)
    normalized = np.clip(normalized * 255.0, 0, 255).astype(np.uint8)
    
    return normalized
