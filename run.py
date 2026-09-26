import sys
import os

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# -----------------------------------------------------------------------
# COMPATIBILITY SHIM — must run before any gradio/spaces import.
# HF ZeroGPU base image ships old gradio that imports HfFolder, which
# was removed in newer huggingface_hub. This shim adds it back.
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
import gradio as gr
import spaces

# -----------------------------------------------------------------------
# REQUIRED by HF ZeroGPU: at least one @spaces.GPU function must exist
# AND be connected to a Gradio event handler.
# -----------------------------------------------------------------------
@spaces.GPU(duration=120)
def gpu_warmup(x):
    """GPU slot holder — actual inference runs via /api/v1/ routes."""
    return "GPU allocated"

# Minimal Gradio UI (required entry point for ZeroGPU Gradio SDK)
with gr.Blocks(title="AquaTrace Backend API") as demo:
    gr.Markdown("## 🌊 AquaTrace Backend API")
    gr.Markdown("**Swagger Docs:** [/docs](/docs)")
    gr.Markdown("**Upload endpoint:** `POST /api/v1/files/upload`")
    # Hidden component wired to our @spaces.GPU function — this is what
    # HF's startup detector looks for to confirm GPU functions exist.
    hidden_in  = gr.Textbox(visible=False)
    hidden_out = gr.Textbox(visible=False)
    hidden_in.submit(fn=gpu_warmup, inputs=[hidden_in], outputs=[hidden_out])

port = 7860 if "SPACE_ID" in os.environ else 8000

# -----------------------------------------------------------------------
# CRITICAL: Use demo.launch() NOT uvicorn.run().
# demo.launch() sets up the ZeroGPU IPC channel with HF's GPU allocator.
# uvicorn.run() bypasses this and causes "No @spaces.GPU detected" error.
# prevent_thread_lock=True returns Gradio's internal FastAPI app so we
# can inject our backend routes into it.
# -----------------------------------------------------------------------
gradio_app, _local_url, _share_url = demo.launch(
    server_name="0.0.0.0",
    server_port=port,
    prevent_thread_lock=True,
    show_error=True,
    quiet=False,
)

# -----------------------------------------------------------------------
# Inject our entire FastAPI backend into Gradio's internal FastAPI app.
# Our routes (/api/v1/*, /docs, /uploads/*) don't conflict with Gradio's
# own routes because they use distinct path prefixes.
# -----------------------------------------------------------------------
from app.api.router import api_router
from app.db.database import engine, Base
from app.models import analysis, sonar_file, detection  # ensure tables created
from app.config import settings
from fastapi.staticfiles import StaticFiles

# Create DB tables
Base.metadata.create_all(bind=engine)

# Add our API routes to Gradio's FastAPI app
gradio_app.include_router(api_router, prefix="/api/v1")

# Serve uploaded images
os.makedirs(settings.upload_dir, exist_ok=True)
gradio_app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir),
    name="uploads"
)

# Block the main thread — keeps the server alive forever
demo.block_thread()
