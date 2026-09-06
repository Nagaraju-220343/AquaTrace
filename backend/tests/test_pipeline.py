import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.api.routes.analysis import execute_full_pipeline
import os
import shutil

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Setup DB
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def test_execute_full_pipeline():
    db = TestingSessionLocal()
    
    # We need a dummy image with enough contrast to pass quality checks
    import numpy as np
    import cv2
    img = np.random.randint(0, 256, (800, 800, 3), dtype=np.uint8)
    cv2.imwrite("test_sonar.jpg", img)
    
    job_id = "JOB-TEST1"
    
    try:
        # Create a mock job in db
        from app.models.analysis import AnalysisJob
        job = AnalysisJob(job_id=job_id, status="PENDING", input_file_path="test_sonar.jpg")
        db.add(job)
        db.commit()
        
        # Execute pipeline
        execute_full_pipeline(job_id, "test_sonar.jpg", db, {})
        
        # Check DB status
        updated_job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        assert updated_job.status == "COMPLETED"
        
        # Check if reports generated
        assert os.path.exists(f"reports/{job_id}_report.json")
        assert os.path.exists(f"reports/{job_id}_report.csv")
        assert os.path.exists(f"reports/{job_id}_report.pdf")
        
    finally:
        db.close()
        if os.path.exists("test_sonar.jpg"):
            os.remove("test_sonar.jpg")
        if os.path.exists("reports"):
            shutil.rmtree("reports")
