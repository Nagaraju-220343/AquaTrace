import math
import json
import logging
from typing import Dict, Any, Tuple, Optional
from pyproj import Geod

logger = logging.getLogger(__name__)

# WGS84 ellipsoid
geod = Geod(ellps="WGS84")

def calculate_geotag(bbox, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates latitude, longitude, and physical dimensions from a pixel bounding box.
    Uses sonar metadata if available.
    """
    # Map UI metadata keys to expected keys
    origin_lat = metadata.get("origin_lat") if metadata.get("origin_lat") is not None else metadata.get("gps_start_lat")
    origin_lon = metadata.get("origin_lon") if metadata.get("origin_lon") is not None else metadata.get("gps_start_lon")

    if not metadata or origin_lat is None or origin_lon is None:
        logger.warning(f"Geotagging UNAVAILABLE — missing GPS. metadata keys: {list(metadata.keys()) if metadata else 'None'}")
        return {
            "geo_status": "UNAVAILABLE",
            "latitude": None,
            "longitude": None,
            "dimensions_meters": None,
            "uncertainty_meters": None
        }
        
    try:
        # Handle bbox stored as JSON string (SQLite/JSON column edge case)
        if isinstance(bbox, str):
            bbox = json.loads(bbox)

        # Extract metadata
        origin_lat = float(origin_lat)
        origin_lon = float(origin_lon)
        heading = float(metadata.get("heading", 0.0))
        
        # meters per pixel (defaulting to 0.1 m/px if unknown)
        mpp = float(metadata.get("meters_per_pixel", 0.1))
        status = "VALID" if "meters_per_pixel" in metadata else "APPROXIMATE"
        
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        
        # Calculate dimensions
        width_m = (x2 - x1) * mpp
        height_m = (y2 - y1) * mpp
        
        origin_x = float(metadata.get("origin_x", 0.0))
        origin_y = float(metadata.get("origin_y", 0.0))
        
        dx_pixels = center_x - origin_x
        dy_pixels = center_y - origin_y
        
        dx_meters = dx_pixels * mpp
        dy_meters = dy_pixels * mpp
        
        # Calculate distance and bearing from origin to anomaly
        distance = math.hypot(dx_meters, dy_meters)
        angle_rad = math.atan2(dx_meters, dy_meters)
        bearing = (heading + math.degrees(angle_rad)) % 360
        
        # Project
        lon, lat, _ = geod.fwd(origin_lon, origin_lat, bearing, distance)
        
        uncertainty = 2.0 if status == "VALID" else 10.0

        logger.info(f"Geotagged: ({origin_lat},{origin_lon}) + {distance:.1f}m @ {bearing:.1f}° → ({lat:.5f},{lon:.5f})")
        
        return {
            "geo_status": status,
            "latitude": round(lat, 7),
            "longitude": round(lon, 7),
            "dimensions_meters": [round(width_m, 2), round(height_m, 2)],
            "uncertainty_meters": uncertainty
        }
        
    except Exception as e:
        logger.error(f"Geotagging failed: {e} | bbox={bbox} | metadata={metadata}", exc_info=True)
        return {
            "geo_status": "UNAVAILABLE",
            "latitude": None,
            "longitude": None,
            "dimensions_meters": None,
            "uncertainty_meters": None
        }
