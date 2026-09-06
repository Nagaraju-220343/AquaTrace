from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AnalysisJobBase(BaseModel):
    pass

class AnalysisJobCreate(AnalysisJobBase):
    job_id: str

class AnalysisJobRead(AnalysisJobBase):
    job_id: str
    status: str
    input_file_path: Optional[str] = None
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
