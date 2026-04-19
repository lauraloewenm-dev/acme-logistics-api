import os
import random
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel

app = FastAPI(title="Acme Logistics Enterprise API")

# --- 🔒 CONFIGURACIÓN DE SEGURIDAD (TODOTERRENO) ---
API_KEY_SECRET = os.getenv("MY_API_KEY", "super-secret-acme-key")

def verify_api_key(request: Request):
    # Opción 1: Comprueba si llega como Header personalizado (X-API-Key)
    api_key = request.headers.get("X-API-Key")
    if api_key == API_KEY_SECRET:
        return api_key
        
    # Opción 2: Comprueba si llega por el estándar Authorization (Bearer Token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        if token == API_KEY_SECRET:
            return token
            
    raise HTTPException(status_code=403, detail="Acceso denegado: API Key inválida")


# --- 📦 GENERADOR AUTOMÁTICO DE BASE DE DATOS ---
def generar_base_de_datos(cantidad=150):
    ciudades = [
        "Chicago, IL", "Dallas, TX", "Miami, FL", "Los Angeles, CA", 
        "Newark, NJ", "Atlanta, GA", "Denver, CO", "Seattle, WA", 
        "Phoenix, AZ", "Columbus, OH", "Savannah, GA", "Houston, TX",
        "Charlotte, NC", "Kansas City, MO", "Laredo, TX"
    ]
    
    equipos_info = {
        "Dry Van": {"commodities": ["Electronics", "Auto Parts", "Textiles", "General Cargo", "Paper Products"], "dims": "53ft"},
        "Reefer": {"commodities": ["Produce", "Frozen Food", "Dairy", "Pharmaceuticals", "Fresh Meat"], "dims": "53ft"},
        "Flatbed": {"commodities": ["Lumber", "Steel Coils", "Machinery", "Building Materials", "Concrete Pipes"], "dims": "48ft"}
    }

    notas_comunes = ["No touch freight", "Tarping required", "Hazmat certified only", "Must have PPE", "Team drivers preferred", "Drop and hook", "Clean trailer required", ""]
    
    nuevas_cargas = []
    
    for i in range(1, cantidad + 1):
        origen = random.choice(ciudades)
        destino = random.choice([c for c in ciudades if c != origen])
        equipo = random.choice(list(equipos_info.keys()))
        commodity = random.choice(equipos_info[equipo]["commodities"])
        
        precio_base = random.randint(80, 450) * 10 
        peso = random.randint(15, 45) * 1000
        
        dias_adelante = random.randint(0, 5)
        fecha_pickup = datetime.now() + timedelta(days=dias_adelante)
        fecha_delivery = fecha_pickup + timedelta(days=random.randint(1, 3))

        carga = {
            "load_id": f"US-{9000 + i}",
            "origin": origen,
            "destination": destino,
            "pickup_datetime": fecha_pickup.strftime("%Y-%m-%d 08:00"),
            "delivery_datetime": fecha_delivery.strftime("%Y-%m-%d 16:00"),
            "equipment_type": equipo,
            "loadboard_rate": precio_base,
            "weight": peso,
            "commodity_type": commodity,
            "num_of_pieces": random.randint(1, 30),
            "miles": random.randint(200, 2000),
            "dimensions": equipos_info[equipo]["dims"],
            "hazmat": random.choice([True, False, False, False]),
            "notes": random.choice(notas_comunes),
            "status": "Available"  # <--- NUEVO: Estado inicial
        }
        nuevas_cargas.append(carga)
        
    return nuevas_cargas

# Generamos las cargas al arrancar el servidor
load_board = generar_base_de_datos(cantidad=150)
call_logs = []

class CallSummary(BaseModel):
    load_id: Optional[str] = None
    carrier_name: Optional[str] = None
    mc_number: Optional[str] = None
    initial_rate: Optional[int] = 0
    agreed_rate: Optional[int] = 0
    call_summary: Optional[str] = None 
    call_outcome: str
    carrier_sentiment: str


# --- 🚀 ENDPOINTS PROTEGIDOS ---

@app.get("/verify-carrier/{mc_number}", dependencies=[Depends(verify_api_key)])
def verify_carrier(mc_number: str):
    api_key = os.getenv("FMCSA_KEY")
    url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "content" in data and len(data["content"]) > 0:
                carrier_info = data["content"][0].get("carrier", {})
                return {"valid": True, "name": carrier_info.get("legalName", "Global Logistics LLC"), "status": "Active"}
        
        nombres_fake = ["Blue Anchor Trans", "Swift Haulage Inc", "Eagle Eye Logistics", "Summit Trucking"]
        nombre_elegido = nombres_fake[int(mc_number) % len(nombres_fake)] if mc_number.isdigit() else "Ace Logistics"
        return {"valid": True, "name": f"{nombre_elegido} (MC {mc_number})", "status": "Active"}
        
    except Exception:
        return {"valid": True, "name": "Acme Partner Carrier", "status": "Active"}


@app.get("/get-loads", dependencies=[Depends(verify_api_key)])
def get_loads(origin: str, equipment: Optional[str] = None):
    search_origin = origin.lower().strip()
    
    # <--- NUEVO: Solo filtramos las que están "Available"
    city_loads = [l for l in load_board if search_origin in l["origin"].lower() and l.get("status") == "Available"]
    
    if not city_loads:
        return {"match_found": False, "message": f"No loads available in {origin} at the moment."}
    
    if equipment:
        search_equip = equipment.lower().strip()
        exact_matches = [l for l in city_loads if search_equip in l["equipment_type"].lower()]
        
        if exact_matches:
            return {"match_found": True, "loads": exact_matches}
        else:
            equipos_disponibles = list(set([l["equipment_type"] for l in city_loads]))
            return {
                "match_found": False,
                "message": f"No {equipment} loads found, but we have alternatives in {origin}.",
                "available_equipment_in_city": equipos_disponibles,
                "alternative_loads": city_loads
            }
            
    return {"match_found": True, "loads": city_loads}


@app.post("/log-call", dependencies=[Depends(verify_api_key)])
def log_call(summary: CallSummary):
    log_entry = summary.dict()
    log_entry["timestamp"] = datetime.now().isoformat()
    call_logs.append(log_entry)

    # <--- NUEVO: Lógica para marcar la carga como "Booked"
    if summary.call_outcome == "Booked" and summary.load_id:
        for load in load_board:
            if load["load_id"] == summary.load_id:
                load["status"] = "Booked"
                break

    return {"status": "success", "message": "Call logged successfully"}


@app.get("/get-logs", dependencies=[Depends(verify_api_key)])
def get_logs():
    return call_logs
