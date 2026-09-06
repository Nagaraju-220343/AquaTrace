from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DetectionRecordSchema(BaseModel):
    object_id: str
    analysis_id: str
    class_name: str = Field(alias="class")
    bbox: List[int] # [x1, y1, x2, y2]
    
    detector_confidence: float
    validation_score: Optional[float] = None
    final_confidence: Optional[float] = None
    decision: Optional[str] = None
    
    source_tile_ids: List[int] = []
    duplicate_count: int = 0
    
    evidence: Optional[Dict[str, float]] = None
    reason: Optional[List[str]] = None
    
    # Geo-tagging fields
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    dimensions_meters: Optional[List[float]] = None
    geo_status: str = "UNAVAILABLE"
    uncertainty_meters: Optional[float] = None

    class Config:
        from_attributes = True
        populate_by_name = True
