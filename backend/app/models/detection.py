from sqlalchemy import Column, String, Float, Integer, JSON
from app.db.database import Base

class DetectionRecord(Base):
    __tablename__ = "detection_records"

    object_id = Column(String, primary_key=True, index=True)
    analysis_id = Column(String, index=True)
    class_name = Column(String)
    
    # Store bbox as JSON list [x1, y1, x2, y2]
    bbox = Column(JSON)
    
    detector_confidence = Column(Float)
    validation_score = Column(Float, nullable=True)
    final_confidence = Column(Float, nullable=True)
    decision = Column(String, nullable=True)
    
    # Extra fields based on NMS and tiling
    source_tile_ids = Column(JSON) # List of tile IDs where this was detected
    duplicate_count = Column(Integer, default=0)
    
    evidence = Column(JSON, nullable=True)
    reason = Column(JSON, nullable=True)
    
    # Geo-tagging fields
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    dimensions_meters = Column(JSON, nullable=True) # [width, height]
    geo_status = Column(String, default="UNAVAILABLE")
    uncertainty_meters = Column(Float, nullable=True)
