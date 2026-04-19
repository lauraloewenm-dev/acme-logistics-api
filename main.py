import os
import random
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF

app = FastAPI(title="Acme Logistics Enterprise API")

# --- 📁 CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS ---
# Esto DEBE ir al principio para evitar errores de ruta
static_path = os.path.join(os.getcwd(), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)

app.mount("/static", StaticFiles(directory=static_path), name="static")

# --- 🔒 SEGURIDAD ---
API_KEY_SECRET = os.getenv("MY_API_KEY", "super-secret-acme-key")

def verify_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if api_key == API_KEY_SECRET:
        return api_key
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        if token == API_KEY_SECRET:
            return token
    raise HTTPException(status_code=403, detail="Acceso denegado: API Key inválida")

# --- 📦 BASE DE DATOS ---
def generar_base_de_datos(cantidad=150):
    ciudades = ["Chicago, IL", "Dallas, TX", "Miami, FL", "Los Angeles, CA", "Newark, NJ", "Atlanta, GA", "Denver, CO", "Seattle, WA", "Phoenix, AZ", "Columbus, OH", "Savannah, GA", "Houston, TX", "Charlotte, NC", "Kansas City, MO", "Laredo, TX"]
    equipos_info = {
        "Dry Van": {"commodities": ["Electronics", "Auto Parts"], "dims": "53ft"},
        "Reefer": {"commodities": ["Produce", "Frozen Food"], "dims": "53ft"},
        "Flatbed": {"commodities": ["Lumber", "Steel Coils"], "dims": "48ft"}
    }
    nuevas_cargas = []
    for i in range(1, cantidad + 1):
        origen = random.choice(ciudades)
        destino = random.choice([c for c in ciudades if c != origen])
        equipo = random.choice(list(equipos_info.keys()))
        nuevas_cargas.append({
            "load_id": f"US-{9000 + i}",
            "origin": origen,
            "destination": destino,
            "pickup_datetime": (datetime.now() + timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d 08:00"),
            "delivery_datetime": (datetime.now() + timedelta(days=random.randint(6, 10))).strftime("%Y-%m-%d 16:00"),
            "equipment_type": equipo,
            "loadboard_rate": random.randint(80, 450) * 10,
            "weight": random.randint(15, 45) * 1000,
            "commodity_type": random.choice(equipos_info[equipo]["commodities"]),
            "status": "Available"
        })
    return nuevas_cargas

load_board = generar_base_de_datos(150)
call_logs = []

class CallSummary(BaseModel):
    load_id: Optional[str] = None
    carrier_name: Optional[str] = None
    agreed_rate: Optional[str] = "0"
    call_outcome: str

# --- 🚀 ENDPOINTS ---

@app.get("/verify-carrier/{mc_number}", dependencies=[Depends(verify_api_key)])
def verify_carrier(mc_number: str):
    # Simulación robusta para que siempre devuelva un nombre si falla la API externa
    nombres_fake = ["Blue Anchor Trans", "Swift Haulage Inc", "Eagle Eye Logistics", "Summit Trucking"]
    nombre_elegido = nombres_fake[int(mc_number) % len(nombres_fake)] if mc_number.isdigit() else "Ace Logistics"
    return {"valid": True, "name": f"{nombre_elegido} (MC {mc_number})", "status": "Active"}

@app.get("/get-loads", dependencies=[Depends(verify_api_key)])
def get_loads(origin: str):
    search_origin = origin.lower().strip()
    match = [l for l in load_board if search_origin in l["origin"].lower() and l["status"] == "Available"]
    return {"match_found": len(match) > 0, "loads": match}

@app.post("/log-call", dependencies=[Depends(verify_api_key)])
def log_call(summary: CallSummary):
    if summary.call_outcome == "Booked" and summary.load_id:
        for load in load_board:
            if load["load_id"] == summary.load_id:
                load["status"] = "Booked"
                break
    call_logs.append(summary.dict())
    return {"status": "success"}

@app.get("/generate-pdf/{load_id}", dependencies=[Depends(verify_api_key)])
def generate_pdf(request: Request, load_id: str, carrier_name: Optional[str] = "Carrier", rate: Optional[str] = "0"):
    try:
        clean_rate = str(rate).replace("$", "").replace(",", "").split(".")[0]
        numeric_rate = int(clean_rate) if clean_rate.isdigit() else 0
    except:
        numeric_rate = 0

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(200, 10, txt="ACME LOGISTICS - RATE CONFIRMATION", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt=f"Load ID: {load_id}", ln=True)
    pdf.cell(200, 10, txt=f"Carrier: {carrier_name}", ln=True)
    pdf.cell(200, 10, txt=f"Agreed Rate: ${numeric_rate}.00", ln=True)
    
    file_name = f"confirmation_{load_id}.pdf"
    file_path = os.path.join(static_path, file_name)
    pdf.output(file_path)
    
    base_url = str(request.base_url).rstrip("/")
    return {"status": "success", "pdf_url": f"{base_url}/static/{file_name}"}
