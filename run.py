import sys
import os

# Add the backend folder to Python's path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# -----------------------------------------------------------------------
# COMPATIBILITY SHIM
# HF's ZeroGPU base image ships an OLD gradio that imports HfFolder from
# huggingface_hub. Newer huggingface_hub removed HfFolder. This shim adds
# it back so gradio's oauth.py import does not crash.
# This must run BEFORE any import of gradio or spaces.
# -----------------------------------------------------------------------
import huggingface_hub as _hfhub
if not hasattr(_hfhub, 'HfFolder'):
    class _HfFolder:
        @staticmethod
        def get_token():
            return (
                os.environ.get('HF_TOKEN')
                or os.environ.get('HUGGING_FACE_HUB_TOKEN')
            )
        @staticmethod
        def save_token(token): pass
        @staticmethod
        def delete_token(): pass
    _hfhub.HfFolder = _HfFolder

# -----------------------------------------------------------------------
# Now safe to import gradio and spaces
# -----------------------------------------------------------------------
import uvicorn
import gradio as gr
import spaces

from app.main import app as fastapi_app

# Required by HF ZeroGPU: at least one @spaces.GPU function must exist
@spaces.GPU(duration=120)
def gpu_inference_handler():
    """GPU slot holder — actual YOLO inference runs via /api/v1/ routes."""
    pass

# Minimal landing page UI
with gr.Blocks(title="AquaTrace Backend API") as demo:
    gr.Markdown("## 🌊 AquaTrace Backend API is Running")
    gr.Markdown("**API Docs (Swagger):** [/docs](/docs)")
    gr.Markdown("**Upload endpoint:** `POST /api/v1/files/upload`")

# Mount Gradio at root "/" — FastAPI routes (/api/v1/, /docs) still work
# because they are matched first (more specific paths take precedence)
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    port = 7860 if "SPACE_ID" in os.environ else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
