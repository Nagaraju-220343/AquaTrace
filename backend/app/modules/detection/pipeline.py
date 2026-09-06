import uuid
import logging
from typing import List, Dict, Any
from numpy import ndarray

from app.modules.detection.model_loader import get_yolo_model
from app.modules.detection.inference import extract_predictions
from app.schemas.detection import DetectionRecordSchema

logger = logging.getLogger(__name__)

def calculate_iou(box1: List[int], box2: List[int]) -> float:
    # box = [x1, y1, x2, y2]
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])

    iou = intersection_area / float(box1_area + box2_area - intersection_area + 1e-6)
    return iou

def global_class_aware_nms(detections: List[Dict], iou_threshold: float = 0.50) -> List[Dict]:
    """
    Applies Non-Maximum Suppression across all tiles, per class.
    Retains the highest confidence detection.
    Merges duplicate counts and source_tile_ids.
    """
    if not detections:
        return []

    # Group by class
    class_groups = {}
    for d in detections:
        c = d["class_name"]
        if c not in class_groups:
            class_groups[c] = []
        class_groups[c].append(d)

    final_detections = []

    for c, class_dets in class_groups.items():
        # Sort by confidence descending
        class_dets.sort(key=lambda x: x["detector_confidence"], reverse=True)
        
        keep = []
        for det in class_dets:
            is_duplicate = False
            for kept_det in keep:
                iou = calculate_iou(det["bbox"], kept_det["bbox"])
                if iou >= iou_threshold:
                    # It's a duplicate of a higher confidence kept_det
                    is_duplicate = True
                    # Merge info
                    kept_det["duplicate_count"] = kept_det.get("duplicate_count", 0) + 1
                    
                    # Merge tile IDs uniquely
                    for tid in det["source_tile_ids"]:
                        if tid not in kept_det["source_tile_ids"]:
                            kept_det["source_tile_ids"].append(tid)
                    break
            
            if not is_duplicate:
                det["duplicate_count"] = 0
                keep.append(det)
                
        final_detections.extend(keep)

    return final_detections

def run_detection_pipeline(
    yolo_images: List[ndarray],
    pipeline_metadata: Dict[str, Any],
    analysis_id: str,
    conf_threshold: float = 0.01,
    iou_threshold: float = 0.50
) -> List[DetectionRecordSchema]:
    """
    Executes detection across all preprocessed images (tiles).
    Applies coordinate reversal and global NMS.
    Returns canonical DetectionRecords.
    """
    model = get_yolo_model() # loads best.pt
    all_detections = []
    
    transforms = pipeline_metadata["transforms"]
    
    for idx, (img, transform_info) in enumerate(zip(yolo_images, transforms)):
        # Run inference
        results = model.predict(source=img, verbose=False, conf=conf_threshold)[0]
        logger.error(f"DEBUG DETECT: tile {idx} -> {len(results.boxes)} raw boxes")
        
        # Extract and reverse coordinates to original image pixels
        dets = extract_predictions(results, transform_info, conf_threshold=conf_threshold)
        logger.error(f"DEBUG DETECT: tile {idx} -> {len(dets)} detections after extract")
        all_detections.extend(dets)
        
    # Apply global class-aware NMS
    suppressed_detections = global_class_aware_nms(all_detections, iou_threshold=iou_threshold)
    
    # Convert to standard schema
    records = []
    for det in suppressed_detections:
        obj_id = f"ANM-{uuid.uuid4().hex[:8].upper()}"
        
        record = DetectionRecordSchema(
            object_id=obj_id,
            analysis_id=analysis_id,
            class_name=det["class_name"],
            bbox=det["bbox"],
            detector_confidence=det["detector_confidence"],
            source_tile_ids=det["source_tile_ids"],
            duplicate_count=det["duplicate_count"]
        )
        records.append(record)
        
    return records
