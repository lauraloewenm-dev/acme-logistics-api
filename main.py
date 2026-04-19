import os
import random
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF

# --- 🗄️ IMPORTACIONES DE BASE DE DATOS (NUEVO) ---
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

app = FastAPI(title="Acme Logistics Enterprise API")

# --- 📁 CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS ---
static_path = os.path.join(os.getcwd(), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# --- 🔒 SEGURIDAD (API KEY) ---
API_KEY_SECRET = os.getenv("MY_API_KEY", "super-secret-acme-key")

def verify_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if api_key == API_KEY_SECRET: return api_key
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        if auth_header.split(" ")[1] == API_KEY_SECRET: return auth_header.split(" ")[1]
    raise HTTPException(status_code=403, detail="Acceso denegado")

# --- 🗄️ CONFIGURACIÓN DE POSTGRESQL (NUEVO) ---
# Railway usa DATABASE_URL. Si pruebas en local y no existe, crea un archivo SQLite.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./acme_local.db")

# Corrección de compatibilidad para Railway/Heroku
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependencia para obtener la sesión de la base de datos en cada endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 📊 MODELOS DE TABLAS DE BASE DE DATOS (NUEVO) ---
class LoadDB(Base):
    __tablename__ = "loads"
    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(String, unique=True, index=True)
    origin = Column(String)
    destination = Column(String)
    pickup_datetime = Column(String)
    delivery_datetime = Column(String)
    equipment_type = Column(String)
    loadboard_rate = Column(Integer)
    weight = Column(Integer)
    commodity_type = Column(String)
    hazmat = Column(Boolean)
    notes = Column(Text)
    status = Column(String, default="Available")

class CallLogDB(Base):
    __tablename__ = "call_logs"
    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(String)
    carrier_name = Column(String)
    mc_number = Column(String)
    initial_rate = Column(Integer)
    agreed_rate = Column(Integer)
    call_summary = Column(Text)
    call_outcome = Column(String)
    carrier_sentiment = Column(String)
    timestamp = Column(String)

# Creamos las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# --- 📋 MODELOS DE PYDANTIC (Para recibir datos del Webhook) ---
class CallSummary(BaseModel):
    load_id: Optional[Any] = "Unknown"
    carrier_name: Optional[Any] = "Unknown"
    mc_number: Optional[Any] = "0"
    initial_rate: Optional[Any] = 0
    agreed_rate: Optional[Any] = 0
    call_summary: Optional[Any] = ""
    call_outcome: Optional[Any] = ""
    carrier_sentiment: Optional[Any] = ""

# --- 📦 POBLAR BASE DE DATOS AL ARRANCAR (NUEVO) ---
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    # Si la tabla de cargas está vacía, generamos 150 cargas iniciales
    if db.query(LoadDB).count() == 0:
        ciudades = ["Chicago, IL", "Dallas, TX", "Miami, FL", "Los Angeles, CA", "Newark, NJ", "Atlanta, GA", "Denver, CO", "Seattle, WA"]
        equipos_info = {"Dry Van": ["Electronics", "Auto Parts"], "Reefer": ["Produce", "Frozen Food"], "Flatbed": ["Lumber", "Steel"]}
        
        for i in range(1, 151):
            origen = random.choice(ciudades)
            destino = random.choice([c for c in ciudades if c != origen])
            equipo = random.choice(list(equipos_info.keys()))
            
            nueva_carga = LoadDB(
                load_id=f"US-{9000 + i}",
                origin=origen,
                destination=destino,
                pickup_datetime=(datetime.now() + timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d 08:00"),
                delivery_datetime=(datetime.now() + timedelta(days=random.randint(6, 10))).strftime("%Y-%m-%d 16:00"),
                equipment_type=equipo,
                loadboard_rate=random.randint(80, 450) * 10,
                weight=random.randint(15, 45) * 1000,
                commodity_type=random.choice(equipos_info[equipo]),
                hazmat=random.choice([True, False, False]),
                notes="No touch freight, clean trailer required.",
                status="Available"
            )
            db.add(nueva_carga)
        db.commit()
        print("✅ Base de datos PostgreSQL poblada con 150 cargas.")
    db.close()


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


# --- 🚀 ENDPOINTS ACTUALIZADOS PARA POSTGRESQL ---

@app.get("/verify-carrier/{mc_number}", dependencies=[Depends(verify_api_key)])
def verify_carrier(mc_number: str):
    nombres_fake = ["Blue Anchor Trans", "Swift Haulage Inc", "Eagle Eye Logistics", "Summit Trucking"]
    nombre_elegido = nombres_fake[int(mc_number) % len(nombres_fake)] if mc_number.isdigit() else "Ace Logistics"
    return {"valid": True, "name": f"{nombre_elegido} (MC {mc_number})", "status": "Active"}

@app.get("/get-loads", dependencies=[Depends(verify_api_key)])
def get_loads(origin: str, db: Session = Depends(get_db)):
    search_origin = origin.lower().strip()
    # Buscar en la base de datos real con ILIKE (insensible a mayúsculas)
    match = db.query(LoadDB).filter(LoadDB.origin.ilike(f"%{search_origin}%"), LoadDB.status == "Available").all()
    return {"match_found": len(match) > 0, "loads": match}

@app.post("/log-call") 
def log_call(summary: CallSummary, db: Session = Depends(get_db)):
    try:
        # 1. Limpiamos los números por si vienen con símbolos ($ o comas)
        def clean_number(val):
            try:
                return int(float(str(val).replace('$', '').replace(',', '').strip()))
            except:
                return 0

        agreed_clean = clean_number(summary.agreed_rate)
        initial_clean = clean_number(summary.initial_rate)

        # 2. Guardamos el log en la base de datos
        nuevo_log = CallLogDB(
            load_id=str(summary.load_id),
            carrier_name=str(summary.carrier_name),
            mc_number=str(summary.mc_number),
            initial_rate=initial_clean,
            agreed_rate=agreed_clean,
            call_summary=str(summary.call_summary),
            call_outcome=str(summary.call_outcome),
            carrier_sentiment=str(summary.carrier_sentiment),
            timestamp=datetime.now().isoformat()
        )
        db.add(nuevo_log)

        # 3. Si es "Booked", actualizamos la carga en la base de datos
        target_id = str(summary.load_id).strip()
        outcome = str(summary.call_outcome).lower()

        if "booked" in outcome and target_id:
            load = db.query(LoadDB).filter(LoadDB.load_id == target_id).first()
            if load:
                load.status = "Booked"
        
        db.commit() # Guardar todos los cambios permanentemente
        return {"status": "success"}
    except Exception as e:
        db.rollback() # Si falla, deshacemos para no corromper la BD
        print(f"Error Database: {e}")
        return {"status": "error", "message": "Salvado por bypass interno"}

@app.get("/generate-pdf/{load_id}", dependencies=[Depends(verify_api_key)])
def generate_pdf(request: Request, load_id: str, carrier_name: str = "Carrier", rate: str = "0", db: Session = Depends(get_db)):
    # Buscar carga en BD
    current_load = db.query(LoadDB).filter(LoadDB.load_id == load_id).first()
    if not current_load:
        raise HTTPException(status_code=404, detail="Load ID not found")

    try:
        numeric_rate = int(str(rate).replace("$", "").replace(",", "").split(".")[0])
    except:
        numeric_rate = 0

    pdf = AcmeConfirmationPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 15, 'OFFICIAL RATE CONFIRMATION', ln=True, align='C')
    pdf.set_font('Helvetica', '', 12)
    pdf.ln(5)
    pdf.cell(0, 10, f"Load ID: {load_id}", ln=True)
    pdf.cell(0, 10, f"Carrier: {carrier_name}", ln=True)
    pdf.cell(0, 10, f"Origin: {current_load.origin} -> Destination: {current_load.destination}", ln=True)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f"Agreed Total Rate: ${numeric_rate:,.2f}", ln=True)
    
    file_name = f"confirmation_{load_id}.pdf"
    file_path = os.path.join(static_path, file_name)
    pdf.output(file_path)
    
    base_url = str(request.base_url).rstrip("/")
    return {"status": "success", "pdf_url": f"{base_url}/static/{file_name}"}

@app.get("/get-logs", dependencies=[Depends(verify_api_key)])
def get_logs(db: Session = Depends(get_db)):
    # Devolver logs desde la BD
    logs = db.query(CallLogDB).all()
    # Convertimos los objetos SQLAlchemy a diccionarios para que el Dashboard (Pandas) los lea
    return [
        {
            "load_id": log.load_id,
            "carrier_name": log.carrier_name,
            "mc_number": log.mc_number,
            "initial_rate": log.initial_rate,
            "agreed_rate": log.agreed_rate,
            "call_summary": log.call_summary,
            "call_outcome": log.call_outcome,
            "carrier_sentiment": log.carrier_sentiment,
            "timestamp": log.timestamp
        }
        for log in logs
    ]
