import pytest
from fastapi.testclient import TestClient
import numpy as np
import cv2
import io
import os

from app.main import app
from app.db.database import Base, engine

# Create tables for tests
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["db"] == "connected"

def test_upload_invalid_image():
    # Test uploading a file with an invalid extension
    response = client.post(
        "/api/v1/upload",
        files={"image": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400
    assert "Invalid extension" in response.json()["detail"]

def test_upload_valid_image_no_meta():
    # Create a valid dummy image using opencv
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    is_success, buffer = cv2.imencode(".png", img)
    assert is_success

    response = client.post(
        "/api/v1/upload",
        files={"image": ("dummy.png", buffer.tobytes(), "image/png")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "PENDING"

def test_upload_valid_image_with_meta():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buffer = cv2.imencode(".jpg", img)

    meta_json = b'{"latitude": "12.34", "longitude": "56.78", "ping_id": "123"}'
    
    response = client.post(
        "/api/v1/upload",
        files={
            "image": ("dummy.jpg", buffer.tobytes(), "image/jpeg"),
            "metadata": ("meta.json", meta_json, "application/json")
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "PENDING"
