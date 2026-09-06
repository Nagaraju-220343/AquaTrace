from typing import List, Dict, Any
from app.schemas.detection import DetectionRecordSchema
from .geotagger import calculate_geotag

def run_geotagging_pipeline(detections: List[DetectionRecordSchema], metadata: Dict[str, Any]) -> List[DetectionRecordSchema]:
    """
    Applies the geotagger to all detections based on the provided metadata.
    Updates schemas in-place.
    """
    for det in detections:
        geo_info = calculate_geotag(det.bbox, metadata)
        
        det.geo_status = geo_info["geo_status"]
        det.latitude = geo_info["latitude"]
        det.longitude = geo_info["longitude"]
        det.dimensions_meters = geo_info["dimensions_meters"]
        det.uncertainty_meters = geo_info["uncertainty_meters"]
        
    return detections
