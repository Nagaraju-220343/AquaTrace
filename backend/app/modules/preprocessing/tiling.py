import numpy as np
from typing import List, Tuple

def conditional_tiling(image: np.ndarray, max_dim: int = 2000, overlap: int = 100) -> List[Tuple[np.ndarray, dict]]:
    """
    If the image is larger than max_dim in either dimension, split it into tiles.
    Returns a list of (tile_image, tile_metadata) tuples.
    Tile metadata includes offset_x and offset_y to map detections back to the original unpadded image.
    If image is smaller than max_dim, returns a single tile.
    """
    h, w = image.shape[:2]
    
    if h <= max_dim and w <= max_dim:
        # No tiling needed
        return [(image, {"offset_x": 0, "offset_y": 0, "is_tiled": False})]
        
    tiles = []
    
    # Calculate step sizes
    step_y = max_dim - overlap
    step_x = max_dim - overlap
    
    for y in range(0, h, step_y):
        for x in range(0, w, step_x):
            y_end = min(y + max_dim, h)
            x_end = min(x + max_dim, w)
            
            # Adjust start to ensure tile is always max_dim if possible, but for edges it might be smaller
            y_start = max(0, y_end - max_dim) if y_end - y < max_dim else y
            x_start = max(0, x_end - max_dim) if x_end - x < max_dim else x
            
            tile = image[y_start:y_end, x_start:x_end]
            
            tile_meta = {
                "offset_x": x_start,
                "offset_y": y_start,
                "is_tiled": True
            }
            tiles.append((tile, tile_meta))
            
    return tiles
