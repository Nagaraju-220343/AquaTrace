"""
Speckle Filter Module
=====================
Side-scan sonar imagery suffers from multiplicative speckle noise — fundamentally
different from additive Gaussian noise in optical imagery. Standard Gaussian/bilateral
filters are inappropriate here.

We implement:
  1. Lee filter (primary) — adaptive sigma-based filter designed for SAR/sonar speckle.
     Computes a local noise estimate and applies adaptive smoothing only where needed.
  2. Median filter (fallback) — fast, edge-preserving, handles impulse/salt-pepper noise.

Reference:
  Lee, J.S. (1980). "Digital Image Enhancement and Noise Filtering by Use of Local Statistics."
  IEEE Transactions on Pattern Analysis and Machine Intelligence, 2(2), 165–168.
"""
import cv2
import numpy as np


def lee_filter(img: np.ndarray, kernel_size: int = 7) -> np.ndarray:
    """
    Apply the Lee adaptive speckle filter to a grayscale image.

    The Lee filter preserves edges by using local statistics (mean, variance)
    to compute a spatially-varying weight k:
        filtered = local_mean + k * (pixel - local_mean)
    where k = local_var / (local_var + noise_var)

    A high k (near 1) means the local region is non-uniform → trust the pixel.
    A low k (near 0) means the region is uniform → replace with local mean.

    Args:
        img: 2D grayscale array (float32 recommended)
        kernel_size: neighbourhood window (odd integer; 7 is a good default for sonar)

    Returns:
        Filtered image, same dtype as input.
    """
    orig_dtype = img.dtype
    img_f = img.astype(np.float32)

    # Local mean (box filter)
    local_mean = cv2.boxFilter(img_f, ddepth=-1, ksize=(kernel_size, kernel_size))

    # Local variance = E[x^2] - E[x]^2
    local_sq_mean = cv2.boxFilter(img_f ** 2, ddepth=-1, ksize=(kernel_size, kernel_size))
    local_var = local_sq_mean - local_mean ** 2
    local_var = np.maximum(local_var, 0)  # numerical safety

    # Estimate global noise variance from a smooth region (5th percentile of local_var)
    noise_var = float(np.percentile(local_var, 5))
    noise_var = max(noise_var, 1e-6)  # avoid divide-by-zero

    # Adaptive weight k
    k = local_var / (local_var + noise_var)

    # Apply filter
    filtered = local_mean + k * (img_f - local_mean)
    filtered = np.clip(filtered, 0, 255)

    return filtered.astype(orig_dtype)


def apply_speckle_filter(image: np.ndarray, method: str = "lee", kernel_size: int = 7) -> np.ndarray:
    """
    Apply speckle noise reduction to a sonar image.

    Args:
        image: BGR or grayscale image (uint8)
        method: "lee" (adaptive, recommended) or "median" (fast fallback)
        kernel_size: kernel/window size (must be odd)

    Returns:
        Filtered image, same shape and dtype as input.
    """
    if kernel_size % 2 == 0:
        kernel_size += 1  # ensure odd

    is_color = len(image.shape) == 3

    if method == "lee":
        if is_color:
            # Filter each channel independently
            channels = cv2.split(image)
            filtered_channels = [lee_filter(c, kernel_size) for c in channels]
            return cv2.merge(filtered_channels)
        else:
            return lee_filter(image, kernel_size)

    elif method == "median":
        return cv2.medianBlur(image, kernel_size)

    else:
        raise ValueError(f"Unknown speckle filter method: {method}. Use 'lee' or 'median'.")
