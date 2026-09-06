import cv2
import numpy as np
from typing import List, Tuple, Dict

from .quality import check_image_quality
from .speckle_filter import apply_speckle_filter
from .motion_artifact import run_motion_artifact_detection
from .resize import letterbox_resize
from .tiling import conditional_tiling

def run_preprocessing_pipeline(
    image: np.ndarray,
    target_size: int = 640,
    max_dim: int = 2000,
    apply_speckle: bool = True,
    speckle_method: str = "lee",
    speckle_kernel: int = 7
) -> Tuple[List[np.ndarray], Dict]:
    """
    Executes the deterministic preprocessing pipeline for sonar images.

    Steps:
        1. Quality check (reject blank/solid images)
        2. Motion artifact detection  (heave/pitch/roll symptom analysis)
        3. Speckle noise reduction    (Lee adaptive filter)
        4. Pass to YOLO               (no manual tiling — YOLO handles its own letterboxing)

    Returns:
        - List of YOLO-ready images (single image, tiling disabled for now)
        - Preprocessing metadata dict with quality, motion, and transform info
    """

    # ── 1. Quality Check ──────────────────────────────────────────────────────
    is_valid, err, quality_metrics = check_image_quality(image)
    if not is_valid:
        raise ValueError(f"Preprocessing aborted. Quality check failed: {err}")

    # ── 2. Motion Artifact Detection ──────────────────────────────────────────
    motion_report = run_motion_artifact_detection(image)

    # ── 3. Speckle Noise Reduction (Lee adaptive filter) ─────────────────────
    if apply_speckle:
        filtered = apply_speckle_filter(image, method=speckle_method, kernel_size=speckle_kernel)
    else:
        filtered = image.copy()

    # ── 4. Build tile list ─────
    h, w = filtered.shape[:2]
    # conditional_tiling returns [(tile_img, {"offset_x": X, "offset_y": Y, "is_tiled": bool}), ...]
    tiles_data = conditional_tiling(filtered, max_dim=target_size, overlap=100)
    
    # Ensure original dimensions are in metadata for the reverse_coordinates function
    for _, meta in tiles_data:
        meta["original_w"] = w
        meta["original_h"] = h

    yolo_images = []
    transforms = []
    for idx, (tile_img, tile_meta) in enumerate(tiles_data):
        tile_meta["tile_index"] = idx
        yolo_images.append(tile_img)
        transforms.append(tile_meta)

    pipeline_metadata = {
        "quality_metrics": quality_metrics,
        "motion_report": motion_report,
        "speckle_filter_applied": apply_speckle,
        "speckle_method": speckle_method,
        "is_tiled": len(yolo_images) > 1,
        "num_tiles": len(yolo_images),
        "target_size": target_size,
        "transforms": transforms
    }

    return yolo_images, pipeline_metadata
