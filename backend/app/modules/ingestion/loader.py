import os
import cv2
import uuid
from fastapi import UploadFile
from typing import Tuple

def load_and_validate_image(file: UploadFile, upload_dir: str) -> Tuple[bool, str, str]:
    """
    Validates file extension, attempts to decode via OpenCV, and saves.
    Returns (is_valid, saved_path, error_message).
    """
    allowed_exts = [".png", ".jpg", ".jpeg", ".tiff", ".tif"]
    ext = os.path.splitext(file.filename)[1].lower()
    
    if ext not in allowed_exts:
        return False, "", f"Invalid extension {ext}. Allowed: {allowed_exts}"

    file_bytes = file.file.read()
    
    # Try decoding image to verify it's readable
    import numpy as np
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return False, "", "Could not decode image file."
        
    # Reset file pointer if needed, but we already have bytes
    # Save the original file untouched
    os.makedirs(upload_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}{ext}"
    saved_path = os.path.join(upload_dir, unique_filename)
    
    with open(saved_path, "wb") as f:
        f.write(file_bytes)
        
    return True, saved_path, ""
