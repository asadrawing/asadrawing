# api_server.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import os
import io
import fitz  # PyMuPDF
import json
import requests
from datetime import datetime
from typing import List

from rule_engine import DrawingRuleEngine
from ai_analyzer import DrawingAIAnalyzer
from dfm_calculator import calculate_advanced_dfm_analysis
from report_generator import generate_qc_report
from history_manager import DrawingHistoryManager

app = FastAPI(
    title="asaDrawing.se REST API - Enterprise Edition",
    description="Utökat API för automatiserad ritningsgranskning, DFM, batch-körningar och ERP/MES-integration.",
    version="2.0.0"
)

OUTPUT_DIR = "rapport"
os.makedirs(OUTPUT_DIR, exist_ok=True)

rule_engine = DrawingRuleEngine()
db_manager = DrawingHistoryManager()

API_SECRET_TOKEN = "asa_secret_api_key_2026"

def verify_token(x_api_key: str):
    if x_api_key != API_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Ogiltig API-nyckel")

def send_webhook_notification(webhook_url: str, payload: dict):
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"Webhook-fel: {str(e)}")

@app.get("/")
def read_root():
    return {"status": "online", "service": "asaDrawing.se API", "version": "2.0.0"}

# 1. Enkel analys (1 fil)
@app.post("/api/v1/analyze", summary="Analysera enskild ritning via REST API")
async def analyze_drawing_api(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form("PROJ-001"),
    revision: str = Form("Rev.A"),
    material: str = Form("Aluminium (Al6061-T6)"),
    length_mm: float = Form(120.0),
    width_mm: float = Form(60.0),
    thickness_mm: float = Form(15.0),
    webhook_url: str = Form(None),
    openai_api_key: str = Form(None),
    x_api_key: str = Header(...)
):
    verify_token(x_api_key)

    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text() + "\n"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Kunde inte läsa PDF: {str(e)}")

    densities = {"Aluminium (Al6061-T6)": 2.70, "Stål (S235JR)": 7.85, "Rostfritt Stål (SS2348)": 8.00}
    density = densities.get(material, 2.70)
    volume_cm3 = (length_mm * width_mm * thickness_mm) / 1000.0
    weight_kg = (volume_cm3 * density) / 1000.0

    rule_issues = rule_engine.evaluate_drawing(extracted_text, {"min_wall_thickness": 2.5, "check_bom": True, "check_gdt": True})

    ai_issues = []
    if openai_api_key:
        ai_analyzer = DrawingAIAnalyzer(api_key=openai_api_key, lang="Swedish")
        metadata_str = f"Projekt: {project_id}, Revision: {revision}, Material: {material}, Mått: {length_mm}x{width_mm}x{thickness_mm} mm"
        ai_issues = ai_analyzer.analyze_drawing_with_ai(extracted_text, metadata_str, {"calc_weight": weight_kg, "calc_volume": volume_cm3, "mat_name": material})

    dfm_res = calculate_advanced_dfm_analysis(material=material, volume_cm3=volume_cm3, weight_kg=weight_kg)
    all_issues = ai_issues + rule_issues

    base_filename = f"API_Rapport_{project_id}_{file.filename.replace('.pdf', '')}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, base_filename)
    generate_qc_report(pdf_path, project_id, file.filename, revision, all_issues)
    
    db_manager.save_inspection(project_id, file.filename, revision, all_issues, pdf_path)

    response_payload = {
        "status": "success",
        "project_id": project_id,
        "filename": file.filename,
        "revision": revision,
        "summary": {
            "total_issues": len(all_issues),
            "estimated_cost_sek": round(dfm_res["total_unit_cost"], 2),
            "machining_time_min": round(dfm_res["machining_time_minutes"], 1),
            "co2e_kg": round(dfm_res["co2_emissions_kg"], 2)
        },
        "issues": all_issues,
        "report_download_url": f"/api/v1/download-report/{base_filename}"
    }

    if webhook_url:
        background_tasks.add_task(send_webhook_notification, webhook_url, response_payload)

    return response_payload

# 2. Batch-analys (Flera filer samtidigt)
@app.post("/api/v1/batch-analyze", summary="Analysera flera ritningar i batch")
async def batch_analyze_api(
    files: List[UploadFile] = File(...),
    project_id: str = Form("PROJ-BATCH"),
    revision: str = Form("Rev.A"),
    material: str = Form("Aluminium (Al6061-T6)"),
    x_api_key: str = Header(...)
):
    verify_token(x_api_key)
    batch_results = []

    for file in files:
        try:
            file_bytes = await file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted_text = ""
            for page in doc:
                extracted_text += page.get_text() + "\n"
            
            vol = 180.0
            wgt = 0.48
            dfm_res = calculate_advanced_dfm_analysis(material=material, volume_cm3=vol, weight_kg=wgt)
            rule_issues = rule_engine.evaluate_drawing(extracted_text, {"min_wall_thickness": 2.5})
            
            base_filename = f"Batch_{project_id}_{file.filename}.pdf".replace(" ", "_")
            pdf_path = os.path.join(OUTPUT_DIR, base_filename)
            generate_qc_report(pdf_path, project_id, file.filename, revision, rule_issues)
            db_manager.save_inspection(project_id, file.filename, revision, rule_issues, pdf_path)

            batch_results.append({
                "filename": file.filename,
                "status": "success",
                "cost_sek": round(dfm_res["total_unit_cost"], 2),
                "issues_count": len(rule_issues)
            })
        except Exception as e:
            batch_results.append({"filename": file.filename, "status": "error", "message": str(e)})

    return {"project_id": project_id, "batch_count": len(files), "results": batch_results}

# 3. Hämta historik över granskningar
@app.get("/api/v1/inspections", summary="Hämta historik över sparade inspektioner")
def get_inspections(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    rows = db_manager.get_all_inspections()
    inspections_list = []
    for r in rows:
        inspections_list.append({
            "id": r[0],
            "project_id": r[1],
            "drawing_name": r[2],
            "revision": r[3],
            "timestamp": r[4],
            "pdf_report": r[6]
        })
    return {"total": len(inspections_list), "inspections": inspections_list}

# 4. Standalone DFM-beräkning
@app.post("/api/v1/calculate-dfm", summary="Beräkna DFM-kostnad direkt via parametrar")
def calculate_dfm_endpoint(
    material: str = Form("Aluminium (Al6061-T6)"),
    length_mm: float = Form(100.0),
    width_mm: float = Form(50.0),
    thickness_mm: float = Form(10.0),
    batch_size: int = Form(1),
    machine_type: str = Form("3-axlig CNC"),
    x_api_key: str = Header(...)
):
    verify_token(x_api_key)
    vol = (length_mm * width_mm * thickness_mm) / 1000.0
    densities = {"Aluminium (Al6061-T6)": 2.70, "Stål (S235JR)": 7.85, "Rostfritt Stål (SS2348)": 8.00}
    wgt = (vol * densities.get(material, 2.70)) / 1000.0

    dfm_res = calculate_advanced_dfm_analysis(
        material=material,
        volume_cm3=vol,
        weight_kg=wgt,
        machine_type=machine_type,
        batch_size=batch_size
    )

    return {
        "material": material,
        "volume_cm3": round(vol, 2),
        "weight_kg": round(wgt, 3),
        "batch_size": batch_size,
        "estimated_cost_sek": round(dfm_res["total_unit_cost"], 2),
        "machining_time_min": round(dfm_res["machining_time_minutes"], 1),
        "co2e_kg": round(dfm_res["co2_emissions_kg"], 2)
    }

@app.get("/api/v1/download-report/{filename}", summary="Ladda ner PDF-rapport via API")
def download_report(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/pdf", filename=filename)
    raise HTTPException(status_code=404, detail="Rapporten hittades inte.")