#!/usr/bin/env python3
"""
ONNX Export & Edge Deployment Benchmark
========================================
Exports the YOLO detection model to ONNX format for edge deployment
and benchmarks inference latency for judges.

Usage:
    python scripts/export_onnx.py [--model models/best.pt] [--imgsz 640] [--quantize]

Output:
    models/best.onnx          — standard FP32 ONNX model
    models/best_report.txt    — latency and size benchmark report

Edge deployment notes:
    - ONNX Runtime supports ARM Cortex-A72 (Raspberry Pi 4, NVIDIA Jetson Nano)
    - No PyTorch required at inference time (only onnxruntime pip package)
    - For Jetson Nano: use TensorRT backend via onnxruntime-gpu
"""
import argparse
import time
import os
import sys
import numpy as np

# Ensure we can import from the backend
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


def export_to_onnx(model_path: str, imgsz: int = 640, output_path: str = None) -> str:
    """Export a YOLO model to ONNX format."""
    from ultralytics import YOLO

    if output_path is None:
        output_path = model_path.replace(".pt", ".onnx")

    print(f"Loading model from: {model_path}")
    model = YOLO(model_path)

    print(f"Exporting to ONNX (imgsz={imgsz})...")
    model.export(format="onnx", imgsz=imgsz, simplify=True, dynamic=False)

    # Ultralytics saves it next to the .pt file
    generated_path = model_path.replace(".pt", ".onnx")
    if generated_path != output_path and os.path.exists(generated_path):
        import shutil
        shutil.move(generated_path, output_path)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Exported to: {output_path} ({size_mb:.1f} MB)")
    return output_path


def benchmark_pytorch(model_path: str, imgsz: int = 640, runs: int = 20) -> dict:
    """Benchmark PyTorch inference latency."""
    from ultralytics import YOLO
    import cv2

    model = YOLO(model_path)
    dummy_img = np.random.randint(0, 255, (imgsz, imgsz, 3), dtype=np.uint8)

    # Warmup
    for _ in range(3):
        model.predict(source=dummy_img, conf=0.01, verbose=False)

    # Benchmark
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        model.predict(source=dummy_img, conf=0.01, verbose=False)
        times.append((time.perf_counter() - t0) * 1000)

    return {
        "backend": "PyTorch (Ultralytics)",
        "mean_ms": round(float(np.mean(times)), 1),
        "std_ms": round(float(np.std(times)), 1),
        "min_ms": round(float(np.min(times)), 1),
        "max_ms": round(float(np.max(times)), 1),
        "runs": runs
    }


def benchmark_onnx(onnx_path: str, imgsz: int = 640, runs: int = 20) -> dict:
    """Benchmark ONNX Runtime inference latency (CPU)."""
    try:
        import onnxruntime as ort
    except ImportError:
        return {"backend": "ONNX Runtime", "error": "onnxruntime not installed. Run: pip install onnxruntime"}

    sess_options = ort.SessionOptions()
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    session = ort.InferenceSession(onnx_path, sess_options, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name

    # ONNX expects NCHW float32
    dummy = np.random.rand(1, 3, imgsz, imgsz).astype(np.float32)

    # Warmup
    for _ in range(3):
        session.run(None, {input_name: dummy})

    # Benchmark
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        session.run(None, {input_name: dummy})
        times.append((time.perf_counter() - t0) * 1000)

    return {
        "backend": "ONNX Runtime (CPU)",
        "mean_ms": round(float(np.mean(times)), 1),
        "std_ms": round(float(np.std(times)), 1),
        "min_ms": round(float(np.min(times)), 1),
        "max_ms": round(float(np.max(times)), 1),
        "runs": runs
    }


def generate_report(model_path: str, onnx_path: str, pytorch_bench: dict, onnx_bench: dict, imgsz: int) -> str:
    """Generate a text benchmark report."""
    pt_size = os.path.getsize(model_path) / (1024 * 1024) if os.path.exists(model_path) else 0
    onnx_size = os.path.getsize(onnx_path) / (1024 * 1024) if os.path.exists(onnx_path) else 0

    report = f"""
╔══════════════════════════════════════════════════════════╗
║       AquaTrace — Edge Deployment Benchmark Report    ║
╚══════════════════════════════════════════════════════════╝

Model: {os.path.basename(model_path)}
Input size: {imgsz}x{imgsz}

━━━ Model Sizes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PyTorch (.pt):    {pt_size:.1f} MB
  ONNX (.onnx):     {onnx_size:.1f} MB

━━━ Inference Latency (CPU, n={pytorch_bench.get('runs', '?')} runs) ━━━━━━━━━━━━━━━━━━━
  PyTorch:
    Mean: {pytorch_bench.get('mean_ms', '?')} ms  |  Std: {pytorch_bench.get('std_ms', '?')} ms
    Min:  {pytorch_bench.get('min_ms', '?')} ms  |  Max: {pytorch_bench.get('max_ms', '?')} ms

  ONNX Runtime (CPU):
    Mean: {onnx_bench.get('mean_ms', onnx_bench.get('error', '?'))} ms  |  Std: {onnx_bench.get('std_ms', '—')} ms
    Min:  {onnx_bench.get('min_ms', '—')} ms  |  Max: {onnx_bench.get('max_ms', '—')} ms

━━━ Edge Deployment Notes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Target hardware: ARM Cortex-A72 (Raspberry Pi 4) equivalent
  Runtime: onnxruntime (no PyTorch required)
  For NVIDIA Jetson: use onnxruntime-gpu with TensorRT backend
  Memory footprint: ~{onnx_size * 3:.0f} MB at runtime (model + activations)

  To install on AUV/edge system:
    pip install onnxruntime numpy opencv-python-headless
    Copy: {os.path.basename(onnx_path)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return report.strip()


def main():
    parser = argparse.ArgumentParser(description="Export YOLO to ONNX and benchmark")
    parser.add_argument("--model", default="models/best.pt", help="Path to .pt model")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--runs", type=int, default=20, help="Benchmark runs")
    parser.add_argument("--skip-export", action="store_true", help="Skip export (use existing .onnx)")
    args = parser.parse_args()

    os.chdir(BACKEND_DIR)

    onnx_path = args.model.replace(".pt", ".onnx")

    # Export
    if not args.skip_export:
        onnx_path = export_to_onnx(args.model, args.imgsz, onnx_path)
    else:
        print(f"Skipping export, using: {onnx_path}")

    # Benchmark
    print("\nBenchmarking PyTorch...")
    pt_bench = benchmark_pytorch(args.model, args.imgsz, args.runs)

    print("Benchmarking ONNX Runtime...")
    onnx_bench = benchmark_onnx(onnx_path, args.imgsz, args.runs)

    # Report
    report = generate_report(args.model, onnx_path, pt_bench, onnx_bench, args.imgsz)
    print("\n" + report)

    report_path = "models/benchmark_report.txt"
    os.makedirs("models", exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
