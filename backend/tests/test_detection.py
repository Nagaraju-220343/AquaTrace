import pytest
from app.modules.detection.inference import reverse_coordinates
from app.modules.detection.pipeline import global_class_aware_nms, calculate_iou

def test_reverse_coordinates():
    # Simulated transform_info from Module 2
    # Original image was 1200x800
    # Tile 1: 0-2000 (meaning it fit in one tile), so it was scaled by 640/1200 = 0.5333
    # New size before padding: 640x426. Padding was (640-426)/2 = 107 top/bottom
    t_info = {
        "original_w": 1200,
        "original_h": 800,
        "scale_r": 640 / 1200.0,
        "pad_w": 0,
        "pad_h": 107,
        "offset_x": 0,
        "offset_y": 0
    }
    
    # Let's say YOLO found a box at padded coords [100, 200, 200, 300]
    bbox = [100.0, 200.0, 200.0, 300.0]
    rev_bbox = reverse_coordinates(bbox, t_info)
    
    # Manual reverse:
    # y1: 200 - 107 = 93. 93 / 0.5333 = 174.375 -> 174
    # x1: 100 - 0 = 100. 100 / 0.5333 = 187.5 -> 188
    # y2: 300 - 107 = 193. 193 / 0.5333 = 361.875 -> 362
    # x2: 200 - 0 = 200. 200 / 0.5333 = 375 -> 375
    
    assert rev_bbox[0] == 188 # x1
    assert rev_bbox[1] == 174 # y1
    assert rev_bbox[2] == 375 # x2
    assert rev_bbox[3] == 362 # y2

def test_iou_calculation():
    box1 = [0, 0, 100, 100]
    box2 = [50, 50, 150, 150]
    iou = calculate_iou(box1, box2)
    
    # Area1 = 10000, Area2 = 10000. Intersection = 50x50 = 2500
    # Union = 20000 - 2500 = 17500. IOU = 2500 / 17500 = 0.1428
    assert round(iou, 2) == 0.14
    
    # Identical boxes
    assert round(calculate_iou(box1, box1), 5) == 1.0
    
    # No overlap
    box3 = [200, 200, 300, 300]
    assert calculate_iou(box1, box3) == 0.0

def test_global_nms():
    detections = [
        {"class_name": "shipwreck", "bbox": [10, 10, 100, 100], "detector_confidence": 0.9, "source_tile_ids": [0]},
        {"class_name": "shipwreck", "bbox": [12, 12, 98, 98], "detector_confidence": 0.7, "source_tile_ids": [1]}, # duplicate
        {"class_name": "crabpot", "bbox": [10, 10, 100, 100], "detector_confidence": 0.8, "source_tile_ids": [0]}, # different class, shouldn't suppress
        {"class_name": "pipeline", "bbox": [200, 200, 300, 300], "detector_confidence": 0.6, "source_tile_ids": [2]}
    ]
    
    final = global_class_aware_nms(detections, iou_threshold=0.5)
    
    assert len(final) == 3
    
    # Shipwreck check
    shipwrecks = [d for d in final if d["class_name"] == "shipwreck"]
    assert len(shipwrecks) == 1
    assert shipwrecks[0]["detector_confidence"] == 0.9
    assert shipwrecks[0]["duplicate_count"] == 1
    assert set(shipwrecks[0]["source_tile_ids"]) == {0, 1}
    
    # Crabpot check
    crabpots = [d for d in final if d["class_name"] == "crabpot"]
    assert len(crabpots) == 1
