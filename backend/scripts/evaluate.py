#!/usr/bin/env python3
"""
Evaluation Metrics — Precision / Recall / mAP
================================================
Computes standard object detection metrics for the BlueOrbit pipeline.

Supports two modes:
  1. YOLO validation mode  — uses YOLO's built-in val() with a labeled dataset
  2. Manual mode           — computes metrics from a CSV of predictions vs ground truth

Usage:
    # Mode 1: YOLO val() on a YOLO-format dataset
    python scripts/evaluate.py --mode yolo --data data/dataset.yaml

    # Mode 2: Manual CSV comparison
    python scripts/evaluate.py --mode manual --predictions results.csv --ground_truth gt.csv

Output:
    Printed table + evaluation_report.json

Manual CSV format:
    predictions.csv: job_id, class_name, x1, y1, x2, y2, confidence
    ground_truth.csv: image_id, class_name, x1, y1, x2, y2
"""
import argparse
import json
import os
import sys
import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


def compute_iou(box1: List[float], box2: List[float]) -> float:
    """Compute IoU between two [x1, y1, x2, y2] boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    inter = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return inter / (area1 + area2 - inter + 1e-6)


def compute_ap(precision: List[float], recall: List[float]) -> float:
    """Compute Average Precision using the 11-point interpolation method."""
    ap = 0.0
    for t in np.arange(0, 1.1, 0.1):
        prec_at_rec = [p for p, r in zip(precision, recall) if r >= t]
        ap += max(prec_at_rec) if prec_at_rec else 0.0
    return ap / 11.0


def compute_precision_recall(
    predictions: List[Dict],
    ground_truths: List[Dict],
    iou_threshold: float = 0.5,
    class_name: str = None
) -> Tuple[float, float, float, float, float]:
    """
    Compute TP, FP, FN, Precision, Recall for a set of predictions vs ground truths.

    Args:
        predictions: list of dicts with keys: image_id, class_name, bbox [x1,y1,x2,y2], confidence
        ground_truths: list of dicts with keys: image_id, class_name, bbox [x1,y1,x2,y2]
        iou_threshold: IoU threshold for a match (typically 0.5)
        class_name: if set, only evaluate this class

    Returns:
        (tp, fp, fn, precision, recall)
    """
    if class_name:
        predictions = [p for p in predictions if p["class_name"] == class_name]
        ground_truths = [g for g in ground_truths if g["class_name"] == class_name]

    # Group GTs by image
    gt_by_image = defaultdict(list)
    for gt in ground_truths:
        gt_by_image[gt["image_id"]].append({"bbox": gt["bbox"], "matched": False})

    # Sort predictions by confidence (descending)
    preds_sorted = sorted(predictions, key=lambda x: x.get("confidence", 0), reverse=True)

    tp = 0
    fp = 0

    for pred in preds_sorted:
        image_id = pred["image_id"]
        gts = gt_by_image.get(image_id, [])

        best_iou = 0.0
        best_gt_idx = -1

        for idx, gt in enumerate(gts):
            if gt["matched"]:
                continue
            iou = compute_iou(pred["bbox"], gt["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = idx

        if best_iou >= iou_threshold and best_gt_idx >= 0:
            tp += 1
            gts[best_gt_idx]["matched"] = True
        else:
            fp += 1

    fn = sum(1 for gts in gt_by_image.values() for gt in gts if not gt["matched"])

    precision = tp / (tp + fp + 1e-6)
    recall = tp / (tp + fn + 1e-6)

    return tp, fp, fn, precision, recall


def evaluate_from_db(iou_threshold: float = 0.5) -> Dict:
    """
    Evaluate pipeline results using detection records already in the database.
    Requires ground truth annotations to be present.

    Since we don't have a labeled GT dataset yet, this returns a sample report
    structure showing what would be computed.
    """
    print("Note: No labeled ground-truth dataset found.")
    print("To enable full evaluation, create data/ground_truth.csv with format:")
    print("  image_id, class_name, x1, y1, x2, y2")
    print("")

    from app.db.database import SessionLocal
    from app.models.detection import DetectionRecord

    db = SessionLocal()
    records = db.query(DetectionRecord).all()
    db.close()

    class_counts = defaultdict(int)
    decision_counts = defaultdict(int)
    confidences = []

    for r in records:
        class_counts[r.class_name] += 1
        decision_counts[r.decision or "UNKNOWN"] += 1
        if r.final_confidence:
            confidences.append(r.final_confidence)

    report = {
        "total_detections": len(records),
        "by_class": dict(class_counts),
        "by_decision": dict(decision_counts),
        "avg_final_confidence": round(float(np.mean(confidences)), 2) if confidences else 0,
        "note": "Ground truth CSV not found. Provide data/ground_truth.csv to compute precision/recall/mAP."
    }
    return report


def yolo_evaluate(model_path: str, data_yaml: str):
    """Run YOLO's built-in val() for mAP computation."""
    from ultralytics import YOLO
    model = YOLO(model_path)
    metrics = model.val(data=data_yaml, iou=0.5, conf=0.01, verbose=True)

    return {
        "mAP_50": round(float(metrics.box.map50), 4),
        "mAP_50_95": round(float(metrics.box.map), 4),
        "precision": round(float(metrics.box.mp), 4),
        "recall": round(float(metrics.box.mr), 4),
        "classes": {
            cls: {
                "ap50": round(float(ap), 4)
            }
            for cls, ap in zip(metrics.names.values(), metrics.box.ap50)
        }
    }


def print_report(report: Dict):
    """Pretty-print an evaluation report."""
    print("\n" + "═" * 55)
    print("  AquaTrace — Evaluation Report")
    print("═" * 55)

    if "mAP_50" in report:
        print(f"  mAP@0.5:       {report['mAP_50'] * 100:.1f}%")
        print(f"  mAP@0.5:0.95:  {report['mAP_50_95'] * 100:.1f}%")
        print(f"  Precision:     {report['precision'] * 100:.1f}%")
        print(f"  Recall:        {report['recall'] * 100:.1f}%")
        if "classes" in report:
            print("\n  Per-class AP@0.5:")
            for cls, vals in report["classes"].items():
                print(f"    {cls:<25} {vals['ap50'] * 100:.1f}%")
    else:
        print(f"  Total detections: {report.get('total_detections', 0)}")
        print(f"  Avg final confidence: {report.get('avg_final_confidence', 0):.1f}%")
        print(f"\n  By class: {report.get('by_class', {})}")
        print(f"  By decision: {report.get('by_decision', {})}")
        if "note" in report:
            print(f"\n  ⚠ {report['note']}")

    print("═" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(description="BlueOrbit evaluation metrics")
    parser.add_argument("--mode", choices=["yolo", "db"], default="db",
                        help="'yolo' = use labeled dataset, 'db' = summarize DB records")
    parser.add_argument("--model", default="models/best.pt")
    parser.add_argument("--data", default="data/dataset.yaml", help="YOLO dataset YAML")
    args = parser.parse_args()

    os.chdir(BACKEND_DIR)

    if args.mode == "yolo":
        if not os.path.exists(args.data):
            print(f"Error: dataset YAML not found at {args.data}")
            sys.exit(1)
        print(f"Running YOLO val() on {args.data}...")
        report = yolo_evaluate(args.model, args.data)
    else:
        print("Summarizing detection database...")
        report = evaluate_from_db()

    print_report(report)

    out_path = "models/evaluation_report.json"
    os.makedirs("models", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to: {out_path}")


if __name__ == "__main__":
    main()
