"""
Motion Artifact Detector
========================
Side-scan sonar AUVs experience three types of motion-induced artifacts:

1. HEAVE (vertical oscillation)  — causes irregular across-track dropout bands
   where the sonar head briefly loses contact range. Appears as horizontal
   stripes of near-zero intensity that interrupt valid echo returns.

2. PITCH (nose up/down)          — causes along-track compression/stretching.
   Objects appear taller or shorter than they are. Manifests as high-frequency
   variation in the nadir (central water column) width.

3. ROLL (side tilt)              — widens the nadir gap on one side and narrows
   it on the other, or creates shadow geometry inconsistencies.

This module detects two primary symptoms:
  a) Nadir width anomalies  → proxy for pitch/roll artifacts
  b) Horizontal dropout bands → proxy for heave artifacts

The detector does NOT attempt to compensate for the motion (that requires raw
ping-level timing data). It instead:
  - Computes a motion_quality_score (0.0 = very bad, 1.0 = clean)
  - Flags row ranges that are likely corrupted
  - These flagged rows are used downstream to penalize detections that overlap them

Reference:
  Cobra, D.T., Oppenheim, A.V., Jaffe, J.S. (1992). "Geometric distortions in
  side-scan sonar images: a procedure for their estimation and correction."
  IEEE J. Ocean. Eng., 17(3), 252–268.
"""
import cv2
import numpy as np
from typing import Dict, List, Any


def detect_nadir(gray: np.ndarray) -> Dict[str, Any]:
    """
    Detect the central nadir (water column) strip in a side-scan sonar image.

    The nadir is characterised by very high pixel intensities (near-white)
    running vertically through the centre of the image.

    Returns:
        dict with keys: centre_col, left_edge, right_edge, width_px, relative_width
    """
    h, w = gray.shape

    # Compute column-wise mean intensity
    col_means = np.mean(gray, axis=0)

    # Nadir = columns with mean > 80th percentile
    threshold = np.percentile(col_means, 80)
    bright_cols = np.where(col_means >= threshold)[0]

    if len(bright_cols) == 0:
        return {"centre_col": w // 2, "left_edge": w // 2, "right_edge": w // 2,
                "width_px": 0, "relative_width": 0.0}

    left_edge = int(bright_cols[0])
    right_edge = int(bright_cols[-1])
    centre_col = (left_edge + right_edge) // 2
    width_px = right_edge - left_edge + 1

    return {
        "centre_col": centre_col,
        "left_edge": left_edge,
        "right_edge": right_edge,
        "width_px": width_px,
        "relative_width": width_px / w
    }


def detect_horizontal_dropout_bands(gray: np.ndarray, threshold_percentile: float = 5.0) -> List[tuple]:
    """
    Detect horizontal rows that are abnormally dark (near-zero intensity).

    In a normal sonar waterfall, rows should have some texture from bottom
    backscatter. Rows with near-zero mean are characteristic of heave-induced
    data dropouts (no valid ping data).

    Args:
        gray: 2D grayscale image
        threshold_percentile: rows with mean below this percentile of all row
                              means are considered dropout candidates.

    Returns:
        List of (start_row, end_row) tuples for contiguous dropout bands.
    """
    row_means = np.mean(gray, axis=1).astype(np.float32)

    # Dynamic threshold: below 5th percentile of row means
    threshold = np.percentile(row_means, threshold_percentile)
    dropout_mask = row_means < threshold

    # Find contiguous bands
    dropout_bands = []
    in_band = False
    band_start = 0

    for i, is_dropout in enumerate(dropout_mask):
        if is_dropout and not in_band:
            band_start = i
            in_band = True
        elif not is_dropout and in_band:
            # Only flag bands > 3 rows wide (single rows may be real dark patches)
            if i - band_start > 3:
                dropout_bands.append((band_start, i - 1))
            in_band = False

    if in_band and len(dropout_mask) - band_start > 3:
        dropout_bands.append((band_start, len(dropout_mask) - 1))

    return dropout_bands


def detect_nadir_width_anomalies(gray: np.ndarray, window_rows: int = 50) -> Dict[str, Any]:
    """
    Track how nadir width changes along the image height (proxy for pitch/roll).

    Divides the image into horizontal strips and measures nadir width in each.
    Large variation = likely pitch/roll motion artifact.

    Returns:
        dict with mean_width, std_width, cv (coefficient of variation), is_anomalous
    """
    h, w = gray.shape
    widths = []

    for y in range(0, h, window_rows):
        strip = gray[y: y + window_rows, :]
        if strip.shape[0] < 5:
            continue
        col_means = np.mean(strip, axis=0)
        threshold = np.percentile(col_means, 80)
        bright_cols = np.where(col_means >= threshold)[0]
        if len(bright_cols) > 0:
            widths.append(bright_cols[-1] - bright_cols[0] + 1)

    if not widths:
        return {"mean_width": 0, "std_width": 0, "cv": 0.0, "is_anomalous": False}

    mean_w = float(np.mean(widths))
    std_w = float(np.std(widths))
    cv = std_w / (mean_w + 1e-6)

    # CV > 0.3 indicates significant width variation (likely pitch/roll)
    is_anomalous = cv > 0.3

    return {
        "mean_width": round(mean_w, 1),
        "std_width": round(std_w, 1),
        "cv": round(cv, 3),
        "is_anomalous": is_anomalous
    }


def run_motion_artifact_detection(image: np.ndarray) -> Dict[str, Any]:
    """
    Main entry point: run all motion artifact checks on a sonar image.

    Args:
        image: BGR or grayscale sonar image (uint8)

    Returns:
        motion_report dict containing:
          - motion_quality_score (0.0 worst → 1.0 clean)
          - flagged_row_ranges: List[(start, end)] rows likely corrupted
          - nadir_info: centre, width, relative_width
          - nadir_anomaly: pitch/roll assessment
          - dropout_bands: heave-induced dropout rows
          - artifact_types: list of detected artifact type strings
    """
    # Convert to grayscale for analysis
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 1. Nadir detection
    nadir_info = detect_nadir(gray)

    # 2. Nadir width variation (pitch/roll proxy)
    nadir_anomaly = detect_nadir_width_anomalies(gray)

    # 3. Horizontal dropout bands (heave proxy)
    dropout_bands = detect_horizontal_dropout_bands(gray)

    # 4. Compute aggregate motion quality score
    # Penalty components:
    #   - Nadir CV > 0.3: subtract 0.3
    #   - Each dropout band: subtract 0.05 (capped at 0.5 total)
    score = 1.0
    artifact_types = []

    if nadir_anomaly["is_anomalous"]:
        penalty = min(0.4, nadir_anomaly["cv"])
        score -= penalty
        artifact_types.append("pitch_roll_nadir_variation")

    dropout_penalty = min(0.5, len(dropout_bands) * 0.05)
    score -= dropout_penalty
    if dropout_bands:
        artifact_types.append("heave_dropout_bands")

    motion_quality_score = max(0.0, round(score, 3))

    return {
        "motion_quality_score": motion_quality_score,
        "flagged_row_ranges": dropout_bands,  # List[(start, end)]
        "nadir_info": nadir_info,
        "nadir_anomaly": nadir_anomaly,
        "dropout_bands": dropout_bands,
        "artifact_types": artifact_types,
        "image_shape": list(image.shape[:2])
    }


def get_row_quality_mask(image_h: int, flagged_row_ranges: List[tuple]) -> np.ndarray:
    """
    Build a boolean mask of shape (image_h,) where True = good row, False = flagged.
    Used downstream to penalize detections overlapping bad rows.
    """
    mask = np.ones(image_h, dtype=bool)
    for start, end in flagged_row_ranges:
        mask[start:end + 1] = False
    return mask
