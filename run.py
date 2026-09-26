import sys
import os

# Add the backend folder to Python's path so 'from app.xxx import ...' works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import uvicorn
import gradio as gr
import spaces

from app.main import app as fastapi_app

# -------------------------------------------------------------------
# ZeroGPU REQUIREMENT: At least one @spaces.GPU function must exist.
# This tells HF's scanner that we are using the GPU and keeps the
# server alive. Our actual YOLO inference is called via FastAPI routes.
# -------------------------------------------------------------------
@spaces.GPU(duration=120)
def gpu_inference_handler():
    """GPU slot holder for ZeroGPU. Actual inference runs via /api/v1/ routes."""
    pass

# -------------------------------------------------------------------
# Minimal Gradio UI — just a landing page.
# All real API traffic goes to /api/v1/ on the FastAPI app.
# -------------------------------------------------------------------
with gr.Blocks(title="AquaTrace Backend API") as demo:
    gr.Markdown("## 🌊 AquaTrace Backend API")
    gr.Markdown("The backend is live. Use the API endpoints below:")
    gr.Markdown("- **API Docs (Swagger):** [/docs](/docs)")
    gr.Markdown("- **Upload & Analyze:** `POST /api/v1/files/upload`")
    gr.Markdown("- **Get Results:** `GET /api/v1/analysis/jobs`")

# Mount our full FastAPI app (with all /api/v1/ routes) as the base.
# Gradio UI is accessible at /ui
app = gr.mount_gradio_app(fastapi_app, demo, path="/ui")

if __name__ == "__main__":
    # On Hugging Face, SPACE_ID is set. Use port 7860 there, 8000 locally.
    port = 7860 if "SPACE_ID" in os.environ else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
