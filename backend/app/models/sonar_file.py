from sqlalchemy import Column, String, Integer, ForeignKey
from app.db.database import Base

class SonarFile(Base):
    __tablename__ = "sonar_files"

    id = Column(String, primary_key=True, index=True)
    analysis_id = Column(String, ForeignKey("analysis_jobs.job_id"))
    original_filename = Column(String)
    file_path = Column(String)
    metadata_path = Column(String, nullable=True)
    
    # Generic metadata fields that might be mapped
    ping_id = Column(Integer, nullable=True)
    timestamp = Column(String, nullable=True)
    range_m = Column(String, nullable=True)
    side = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    heading = Column(String, nullable=True)
