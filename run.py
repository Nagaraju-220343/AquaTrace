import uvicorn
import sys
import os

# Add the backend folder to Python's path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.main import app

if __name__ == "__main__":
    port = 7860 if "SPACE_ID" in os.environ else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
