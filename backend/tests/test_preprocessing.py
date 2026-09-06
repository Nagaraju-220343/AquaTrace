import pytest
import numpy as np
from app.modules.preprocessing.quality import check_image_quality
from app.modules.preprocessing.normalization import apply_percentile_normalization
from app.modules.preprocessing.resize import letterbox_resize
from app.modules.preprocessing.tiling import conditional_tiling
from app.modules.preprocessing.pipeline import run_preprocessing_pipeline

def test_quality_check():
    # Solid black image
    img = np.zeros((100, 100), dtype=np.uint8)
    is_valid, err, _ = check_image_quality(img)
    assert not is_valid
    
    # Normal image with some noise/variation
    img2 = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    is_valid, err, _ = check_image_quality(img2)
    assert is_valid

def test_percentile_normalization():
    img = np.array([[10, 50, 100], [20, 150, 200]], dtype=np.uint8)
    norm = apply_percentile_normalization(img)
    
    assert norm.shape == img.shape
    assert np.min(norm) < np.min(img) # Should be stretched closer to 0
    assert np.max(norm) > np.max(img) # Should be stretched closer to 255

def test_resize_padding():
    img = np.zeros((200, 400, 3), dtype=np.uint8) # w > h
    padded, t_info = letterbox_resize(img, target_size=640)
    
    assert padded.shape == (640, 640, 3)
    assert t_info["original_w"] == 400
    assert t_info["original_h"] == 200
    assert t_info["scale_r"] == 640 / 400  # 1.6
    
    # New h = 200 * 1.6 = 320. Pad = (640 - 320)/2 = 160 top and bottom
    assert t_info["pad_h"] == 160
    assert t_info["pad_w"] == 0

def test_tiling():
    img = np.zeros((2500, 1000, 3), dtype=np.uint8)
    tiles = conditional_tiling(img, max_dim=2000, overlap=100)
    
    assert len(tiles) == 2
    assert tiles[0][0].shape == (2000, 1000, 3)
    assert tiles[1][0].shape == (2000, 1000, 3) # Even the second tile should be max_dim size since we adjust y_start
    
    # Tile 2 offset should be 2500 - 2000 = 500
    assert tiles[1][1]["offset_y"] == 500

def test_full_pipeline():
    # Valid random noise image (so it passes quality)
    img = np.random.randint(0, 255, (800, 1200, 3), dtype=np.uint8)
    
    tiles, metadata = run_preprocessing_pipeline(img, target_size=640, max_dim=2000)
    
    assert metadata["is_tiled"] == False
    assert len(tiles) == 1
    assert tiles[0].shape == (640, 640, 3)
    
    # The transform should scale by 640/1200
    assert metadata["transforms"][0]["scale_r"] == 640 / 1200
