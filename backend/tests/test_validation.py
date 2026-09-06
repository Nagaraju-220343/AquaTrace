import pytest
import numpy as np
from app.modules.validation.cropper import extract_contextual_crop
from app.modules.validation.lightweight_checks import run_lightweight_checks
from app.schemas.detection import DetectionRecordSchema

def test_extract_contextual_crop():
    # 100x100 image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Bbox: 40x40 square in the center
    bbox = [30, 30, 70, 70] 
    
    # Padding 25% of 40 = 10
    # Expected crop coords: x1=20, y1=20, x2=80, y2=80. Size = 60x60
    crop, local_bbox = extract_contextual_crop(img, bbox, padding_percent=0.25)
    
    assert crop.shape == (60, 60, 3)
    
    # Old x1 was 30. Crop x1 is 20. Local x1 should be 10.
    assert local_bbox == [10, 10, 50, 50]

def test_extract_contextual_crop_edge():
    # 100x100 image, bbox on the top-left edge
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    bbox = [0, 0, 40, 40]
    
    # pad = 10. Expected crop coords: x1=0 (clamped), y1=0 (clamped), x2=50, y2=50.
    crop, local_bbox = extract_contextual_crop(img, bbox, padding_percent=0.25)
    
    assert crop.shape == (50, 50, 3)
    assert local_bbox == [0, 0, 40, 40]

def test_lightweight_checks():
    img = np.zeros((100, 100), dtype=np.uint8)
    # Put a bright square inside
    img[30:70, 30:70] = 255
    
    bbox = [30, 30, 70, 70]
    local_bbox = [30, 30, 70, 70] # Assuming it's already cropped/sized
    
    evidence = run_lightweight_checks(img, local_bbox, bbox)
    
    assert "size_score" in evidence
    assert "contrast_score" in evidence
    assert "texture_score" in evidence
    assert "validation_score" in evidence
    
    assert evidence["size_score"] > 0 # (40*40)/2500 = 1600/2500 = 0.64
