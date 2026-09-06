import os
import json
import csv
from typing import List
from app.schemas.detection import DetectionRecordSchema
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

REPORT_DIR = "reports"

def ensure_report_dir():
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)

def generate_json_report(analysis_id: str, detections: List[DetectionRecordSchema]) -> str:
    ensure_report_dir()
    filepath = os.path.join(REPORT_DIR, f"{analysis_id}_report.json")
    
    data = [det.model_dump() for det in detections]
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        
    return filepath

def generate_csv_report(analysis_id: str, detections: List[DetectionRecordSchema]) -> str:
    ensure_report_dir()
    filepath = os.path.join(REPORT_DIR, f"{analysis_id}_report.csv")
    
    if not detections:
        with open(filepath, 'w', newline='') as f:
            f.write("No detections found.")
        return filepath
        
    # Get headers from the first schema
    headers = list(detections[0].model_dump().keys())
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for det in detections:
            # Flatten lists/dicts to strings for CSV
            row = det.model_dump()
            row["bbox"] = json.dumps(row["bbox"])
            row["source_tile_ids"] = json.dumps(row["source_tile_ids"])
            row["evidence"] = json.dumps(row["evidence"]) if row["evidence"] else ""
            row["reason"] = json.dumps(row["reason"]) if row["reason"] else ""
            row["dimensions_meters"] = json.dumps(row["dimensions_meters"]) if row["dimensions_meters"] else ""
            writer.writerow(row)
            
    return filepath

def generate_pdf_report(analysis_id: str, detections: List[DetectionRecordSchema]) -> str:
    ensure_report_dir()
    filepath = os.path.join(REPORT_DIR, f"{analysis_id}_report.pdf")
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    title = Paragraph(f"AquaTrace - Analysis Report: {analysis_id}", styles['Title'])
    elements.append(title)
    
    if not detections:
        elements.append(Paragraph("No anomalies detected.", styles['Normal']))
        doc.build(elements)
        return filepath
        
    # Table headers
    data = [["Object ID", "Class", "Decision", "Confidence", "Lat/Lon", "Reason"]]
    
    for det in detections:
        lat_lon = f"{det.latitude}, {det.longitude}" if det.geo_status == "VALID" else det.geo_status
        reasons = ", ".join(det.reason) if det.reason else ""
        row = [
            det.object_id,
            det.class_name,
            det.decision,
            f"{det.final_confidence}%" if det.final_confidence else "N/A",
            lat_lon,
            reasons
        ]
        data.append(row)
        
    table = Table(data, colWidths=[80, 80, 60, 60, 100, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return filepath

def generate_all_reports(analysis_id: str, detections: List[DetectionRecordSchema]):
    json_path = generate_json_report(analysis_id, detections)
    csv_path = generate_csv_report(analysis_id, detections)
    pdf_path = generate_pdf_report(analysis_id, detections)
    return {"json": json_path, "csv": csv_path, "pdf": pdf_path}
