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

class AcmeConfirmationPDF(FPDF):
    def header(self):
        # Logo o Nombre de Empresa Estilizado
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(31, 78, 120) # Azul oscuro corporativo
        self.cell(0, 10, 'ACME LOGISTICS ENTERPRISE', ln=True, align='L')
        
        # Línea divisoria decorativa
        self.set_draw_color(31, 78, 120)
        self.set_line_width(0.5)
        self.line(10, 22, 200, 22)
        
        # Info de contacto de ACME (falsa pero pro)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(100)
        self.set_xy(140, 10)
        self.multi_cell(60, 4, '123 Logistics Way, Chicago, IL 60601\nPhone: (555) 012-3456\ndispatch@acmelogistics.com', align='R')
        self.ln(12)

    def footer(self):
        # Pie de página con número y aviso de automatización
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150)
        aviso = "This is an automated document generated by ACME Logistics AI Voice System. No signature required."
        self.cell(0, 10, aviso, align='C')
        self.set_x(180)
        self.cell(0, 10, f'Page {self.page_no()}', align='R')

# --- ENDPOINT DE GENERACIÓN DE PDF ACTUALIZADO ---
@app.get("/generate-pdf/{load_id}", dependencies=[Depends(verify_api_key)])
def generate_pdf(request: Request, load_id: str, carrier_name: Optional[str] = "Carrier", rate: Optional[str] = "0"):
    
    # 1. Recuperar TODA la información de la carga de la base de datos interna
    current_load = None
    for load in load_board:
        if load["load_id"] == load_id:
            current_load = load
            break
            
    # Si no encontramos la carga, no podemos hacer un PDF pro
    if not current_load:
        raise HTTPException(status_code=404, detail=f"Load ID {load_id} not found in database.")

    # 2. Limpieza de seguridad del precio (lo recibimos como str, lo usamos como int)
    try:
        clean_rate = str(rate).replace("$", "").replace(",", "").split(".")[0].strip()
        numeric_rate = int(clean_rate) if clean_rate.isdigit() else 0
    except:
        numeric_rate = 0

    # 3. Formatear la información para el documento
    is_hazmat = "YES" if current_load.get("hazmat", False) else "NO"
    weight_str = f"{current_load['weight']:,} lbs" # Formato con comas para miles
    rate_str = f"${numeric_rate:,.2f}" # Formato de dinero profesional

    # 4. Crear el PDF usando la clase personalizada
    pdf = AcmeConfirmationPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Título Principal del Documento
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(46, 117, 182) # Azul un poco más claro
    pdf.cell(0, 15, 'OFFICIAL RATE CONFIRMATION', ln=True, align='C')
    pdf.ln(5)

    # --- SECCIÓN 1: RESUMEN DEL ACUERDO ---
    # Colores de fondo para tablas (gris muy suave)
    fill_color = (242, 242, 242)
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_fill_color(*fill_color)
    pdf.cell(0, 8, ' AGREMEENT SUMMARY', ln=True, fill=True)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0)
    
    # Tabla de resumen (usando celdas alineadas)
    col1 = 30
    col2 = 70
    
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(col1, 7, 'Load ID:'); pdf.set_font('Helvetica', '', 10); pdf.cell(col2, 7, load_id)
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(col1, 7, 'Document Date:'); pdf.set_font('Helvetica', '', 10); pdf.cell(col2, 7, datetime.now().strftime('%Y-%m-%d'), ln=True)
    
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(col1, 7, 'Carrier:'); pdf.set_font('Helvetica', '', 10); pdf.cell(col2, 7, carrier_name)
    pdf.set_font('Helvetica', 'B', 10); pdf.cell(col1, 7, 'Agreed Rate:'); pdf.set_font('Helvetica', 'B', 11); pdf.set_text_color(0, 128, 0); pdf.cell(col2, 7, rate_str, ln=True) # Verde para dinero
    pdf.set_text_color(0) # Reset color

    pdf.ln(10)

    # --- SECCIÓN 2: PICKUP & DELIVERY DETAILS ---
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_fill_color(*fill_color)
    pdf.cell(0, 8, ' ROUTE & SCHEDULE DETAILS', ln=True, fill=True)
    pdf.ln(4)
    
    # Tabla profesional para Origen/Destino
    pdf.set_font('Helvetica', 'B', 9)
    # Encabezados de tabla
    pdf.cell(20, 7, '', align='C') # Espacio
    pdf.cell(70, 7, 'LOCATION', border=1, align='C')
    pdf.cell(70, 7, 'DATE & TIME', border=1, align='C', ln=True)
    
    # Contenido de tabla
    pdf.set_font('Helvetica', '', 10)
    # Origin
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(20, 7, 'ORIGIN:', align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(70, 7, current_load['origin'], border=1, align='L')
    pdf.cell(70, 7, current_load['pickup_datetime'], border=1, align='C', ln=True)
    
    # Destination
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(20, 7, 'DEST:', align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(70, 7, current_load['destination'], border=1, align='L')
    pdf.cell(70, 7, current_load['delivery_datetime'], border=1, align='C', ln=True)
    
    pdf.ln(10)

    # --- SECCIÓN 3: EQUIPMENT & CARGO INFO ---
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_fill_color(*fill_color)
    pdf.cell(0, 8, ' EQUIPMENT & CARGO REQUIREMENTS', ln=True, fill=True)
    pdf.ln(4)
    
    # Tabla profesional para equipo
    pdf.set_font('Helvetica', 'B', 9)
    # Encabezados de tabla
    pdf.cell(45, 7, 'EQUIPMENT TYPE', border=1, align='C')
    pdf.cell(45, 7, 'COMMODITY', border=1, align='C')
    pdf.cell(45, 7, 'WEIGHT', border=1, align='C')
    pdf.cell(45, 7, 'HAZMAT', border=1, align='C', ln=True)
    
    # Contenido de tabla
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(45, 8, current_load['equipment_type'], border=1, align='C')
    pdf.cell(45, 8, current_load['commodity_type'], border=1, align='C')
    pdf.cell(45, 8, weight_str, border=1, align='C')
    
    # Color rojo si es Hazmat
    if current_load.get("hazmat", False):
        pdf.set_text_color(192, 0, 0)
        pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(45, 8, is_hazmat, border=1, align='C', ln=True)
    pdf.set_text_color(0) # Reset
    pdf.set_font('Helvetica', '', 10)

    pdf.ln(10)

    # --- SECCIÓN 4: DRIVER REQUIREMENTS & NOTES ---
    if current_load['notes']:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_fill_color(*fill_color)
        pdf.cell(0, 8, ' DRIVER REQUIREMENTS & SPECIAL NOTES', ln=True, fill=True)
        pdf.ln(3)
        
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(80)
        # multi_cell para textos largos que necesitan saltos de línea automáticos
        pdf.multi_cell(0, 5, f"- {current_load['notes']}", align='L')
        
        # Añadir notas estándar obligatorias
        pdf.multi_cell(0, 5, "- No touch freight. Driver must remain in cab during loading/unloading.", align='L')
        if current_load.get("hazmat", False):
            pdf.set_font('Helvetica', 'BI', 10)
            pdf.set_text_color(192, 0, 0)
            pdf.multi_cell(0, 5, "- Driver must have HAZMAT endorsement. Proper placarding required.", align='L')

    # 5. Guardar y generar URL (Lógica existente)
    file_name = f"confirmation_{load_id}.pdf"
    file_path = f"static/{file_name}"
    pdf.output(file_path)
    
    base_url = str(request.base_url).rstrip("/")
    full_pdf_url = f"{base_url}/static/{file_name}"
    
    return {
        "status": "success",
        "load_id": load_id,
        "pdf_url": full_pdf_url
    }
