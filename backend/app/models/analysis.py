from sqlalchemy import Column, String, DateTime, Enum
from app.db.database import Base
from datetime import datetime
import enum

class JobStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    job_id = Column(String, primary_key=True, index=True)
    status = Column(String, default="PENDING")
    input_file_path = Column(String, nullable=True)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
