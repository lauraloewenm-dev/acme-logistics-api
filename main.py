import os
import random
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF

app = FastAPI(title="Acme Logistics Enterprise API")

# --- 📁 CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS ---
# Crea la carpeta para que los PDFs sean accesibles vía URL
static_path = os.path.join(os.getcwd(), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)

app.mount("/static", StaticFiles(directory=static_path), name="static")

# --- 🔒 SEGURIDAD (API KEY) ---
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

# --- 📦 BASE DE DATOS DINÁMICA ---
def generar_base_de_datos(cantidad=150):
    ciudades = ["Chicago, IL", "Dallas, TX", "Miami, FL", "Los Angeles, CA", "Newark, NJ", "Atlanta, GA", "Denver, CO", "Seattle, WA", "Phoenix, AZ", "Columbus, OH", "Savannah, GA", "Houston, TX", "Charlotte, NC", "Kansas City, MO", "Laredo, TX"]
    equipos_info = {
        "Dry Van": {"commodities": ["Electronics", "Auto Parts", "Textiles"], "dims": "53ft"},
        "Reefer": {"commodities": ["Produce", "Frozen Food", "Dairy"], "dims": "53ft"},
        "Flatbed": {"commodities": ["Lumber", "Steel Coils", "Machinery"], "dims": "48ft"}
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
            "hazmat": random.choice([True, False, False]),
            "notes": "No touch freight, clean trailer required.",
            "status": "Available"
        })
    return nuevas_cargas

# Generamos la base de datos en memoria al arrancar
load_board = generar_base_de_datos(150)
call_logs = []

# --- 📋 MODELOS DE DATOS ---
class CallSummary(BaseModel):
    load_id: Optional[Any] = "Unknown"
    carrier_name: Optional[Any] = "Unknown"
    mc_number: Optional[Any] = "0"
    initial_rate: Optional[Any] = 0
    agreed_rate: Optional[Any] = 0
    call_summary: Optional[Any] = ""
    call_outcome: Optional[Any] = ""
    carrier_sentiment: Optional[Any] = ""

# --- 🎨 CLASE PDF PROFESIONAL ---
class AcmeConfirmationPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(31, 78, 120)
        self.cell(0, 10, 'ACME LOGISTICS ENTERPRISE', ln=True, align='L')
        self.set_draw_color(31, 78, 120)
        self.line(10, 22, 200, 22)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(100)
        self.set_xy(140, 10)
        self.multi_cell(60, 4, '123 Logistics Way, Chicago, IL\nPhone: (555) 012-3456', align='R')
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150)
        self.cell(0, 10, 'Automated Document - No Signature Required', align='C')

# --- 🚀 ENDPOINTS ---

@app.get("/verify-carrier/{mc_number}", dependencies=[Depends(verify_api_key)])
def verify_carrier(mc_number: str):
    nombres_fake = ["Blue Anchor Trans", "Swift Haulage Inc", "Eagle Eye Logistics", "Summit Trucking"]
    nombre_elegido = nombres_fake[int(mc_number) % len(nombres_fake)] if mc_number.isdigit() else "Ace Logistics"
    return {"valid": True, "name": f"{nombre_elegido} (MC {mc_number})", "status": "Active"}

@app.get("/get-loads", dependencies=[Depends(verify_api_key)])
def get_loads(origin: str):
    search_origin = origin.lower().strip()
    match = [l for l in load_board if search_origin in l["origin"].lower() and l["status"] == "Available"]
    return {"match_found": len(match) > 0, "loads": match}

@app.post("/log-call") # Sin dependencia para asegurar que el dashboard reciba datos
def log_call(summary: CallSummary):
    try:
        log_entry = summary.dict()
        log_entry["timestamp"] = datetime.now().isoformat()
        call_logs.append(log_entry)

        # Actualizar estado a Booked
        target_id = str(summary.load_id).strip()
        outcome = str(summary.call_outcome).lower()

        if "booked" in outcome and target_id:
            for load in load_board:
                if load["load_id"] == target_id:
                    load["status"] = "Booked"
                    break
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/generate-pdf/{load_id}", dependencies=[Depends(verify_api_key)])
def generate_pdf(request: Request, load_id: str, carrier_name: str = "Carrier", rate: str = "0"):
    # Buscar datos de la carga en memoria
    current_load = next((l for l in load_board if l["load_id"] == load_id), None)
    if not current_load:
        raise HTTPException(status_code=404, detail="Load ID not found")

    # Limpieza de precio
    try:
        numeric_rate = int(str(rate).replace("$", "").replace(",", "").split(".")[0])
    except:
        numeric_rate = 0

    # Crear PDF
    pdf = AcmeConfirmationPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 15, 'OFFICIAL RATE CONFIRMATION', ln=True, align='C')
    
    pdf.set_font('Helvetica', '', 12)
    pdf.ln(5)
    pdf.cell(0, 10, f"Load ID: {load_id}", ln=True)
    pdf.cell(0, 10, f"Carrier: {carrier_name}", ln=True)
    pdf.cell(0, 10, f"Origin: {current_load['origin']} -> Destination: {current_load['destination']}", ln=True)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f"Agreed Total Rate: ${numeric_rate:,.2f}", ln=True)
    
    file_name = f"confirmation_{load_id}.pdf"
    file_path = os.path.join(static_path, file_name)
    pdf.output(file_path)
    
    base_url = str(request.base_url).rstrip("/")
    return {"status": "success", "pdf_url": f"{base_url}/static/{file_name}"}

@app.get("/get-logs", dependencies=[Depends(verify_api_key)])
def get_logs():
    # Creamos una copia de los logs para no romper la memoria
    processed_logs = []
    
    for log in call_logs:
        new_log = log.copy()
        try:
            # Limpiamos y convertimos agreed_rate a número
            agreed = str(new_log.get('agreed_rate', '0')).replace('$', '').replace(',', '').strip()
            new_log['agreed_rate'] = int(float(agreed)) if agreed else 0
            
            # Limpiamos y convertimos initial_rate a número
            initial = str(new_log.get('initial_rate', '0')).replace('$', '').replace(',', '').strip()
            new_log['initial_rate'] = int(float(initial)) if initial else 0
        except:
            # Si falla la conversión, ponemos 0 para que el dashboard no explote
            new_log['agreed_rate'] = 0
            new_log['initial_rate'] = 0
            
        processed_logs.append(new_log)
        
    return processed_logs
