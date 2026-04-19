import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Acme Logistics Enterprise API")


load_board = [
    {"load_id": "US-9901", "origin": "Chicago, IL", "destination": "Dallas, TX", "pickup_datetime": "2026-04-20 08:00", "delivery_datetime": "2026-04-22 18:00", "equipment_type": "Dry Van", "loadboard_rate": 2400, "weight": 42000, "commodity_type": "Electronics", "num_of_pieces": 22, "miles": 920, "dimensions": "53ft", "hazmat": False, "notes": "No touch freight"},
    {"load_id": "US-9902", "origin": "Houston, TX", "destination": "Miami, FL", "pickup_datetime": "2026-04-21 06:00", "delivery_datetime": "2026-04-23 12:00", "equipment_type": "Reefer", "loadboard_rate": 3100, "weight": 35000, "commodity_type": "Frozen Food", "num_of_pieces": 18, "miles": 1180, "dimensions": "48ft", "hazmat": False, "notes": "Maintain -10 degrees"},
    {"load_id": "US-9903", "origin": "Savannah, GA", "destination": "Nashville, TN", "pickup_datetime": "2026-04-20 14:00", "delivery_datetime": "2026-04-21 09:00", "equipment_type": "Flatbed", "loadboard_rate": 1550, "weight": 45000, "commodity_type": "Steel Coils", "num_of_pieces": 4, "miles": 490, "dimensions": "48ft", "hazmat": False, "notes": "Tarping required"},
    {"load_id": "US-9904", "origin": "Los Angeles, CA", "destination": "Phoenix, AZ", "pickup_datetime": "2026-04-22 07:00", "delivery_datetime": "2026-04-22 20:00", "equipment_type": "Dry Van", "loadboard_rate": 1100, "weight": 12000, "commodity_type": "Textiles", "num_of_pieces": 10, "miles": 370, "dimensions": "53ft", "hazmat": False, "notes": "High value load"},
    {"load_id": "US-9905", "origin": "Newark, NJ", "destination": "Cleveland, OH", "pickup_datetime": "2026-04-20 10:00", "delivery_datetime": "2026-04-21 06:00", "equipment_type": "Dry Van", "loadboard_rate": 1900, "weight": 38000, "commodity_type": "General Cargo", "num_of_pieces": 24, "miles": 430, "dimensions": "53ft", "hazmat": True, "notes": "Hazmat certified only"},
    {"load_id": "US-9906", "origin": "Denver, CO", "destination": "Salt Lake City, UT", "pickup_datetime": "2026-04-23 08:00", "delivery_datetime": "2026-04-23 20:00", "equipment_type": "Reefer", "loadboard_rate": 1450, "weight": 40000, "commodity_type": "Produce", "num_of_pieces": 20, "miles": 520, "dimensions": "53ft", "hazmat": False, "notes": "E-track required"},
    {"load_id": "US-9907", "origin": "Laredo, TX", "destination": "Chicago, IL", "pickup_datetime": "2026-04-21 12:00", "delivery_datetime": "2026-04-24 08:00", "equipment_type": "Dry Van", "loadboard_rate": 3800, "weight": 44000, "commodity_type": "Auto Parts", "num_of_pieces": 26, "miles": 1350, "dimensions": "53ft", "hazmat": False, "notes": "Team drivers preferred"},
    {"load_id": "US-9908", "origin": "Seattle, WA", "destination": "Portland, OR", "pickup_datetime": "2026-04-20 09:00", "delivery_datetime": "2026-04-20 15:00", "equipment_type": "Flatbed", "loadboard_rate": 850, "weight": 48000, "commodity_type": "Lumber", "num_of_pieces": 12, "miles": 175, "dimensions": "48ft", "hazmat": False, "notes": "Side kit needed"},
    {"load_id": "US-9909", "origin": "Atlanta, GA", "destination": "Charlotte, NC", "pickup_datetime": "2026-04-22 11:00", "delivery_datetime": "2026-04-22 17:00", "equipment_type": "Dry Van", "loadboard_rate": 950, "weight": 15000, "commodity_type": "Paper Products", "num_of_pieces": 14, "miles": 245, "dimensions": "53ft", "hazmat": False, "notes": "Quick turn around"},
    {"load_id": "US-9910", "origin": "Kansas City, MO", "destination": "Columbus, OH", "pickup_datetime": "2026-04-21 16:00", "delivery_datetime": "2026-04-22 10:00", "equipment_type": "Reefer", "loadboard_rate": 1750, "weight": 30000, "commodity_type": "Dairy", "num_of_pieces": 16, "miles": 650, "dimensions": "53ft", "hazmat": False, "notes": "Washout receipt required"}
]

FMCSA_API_KEY = os.getenv("FMCSA_KEY")

# --- ENDPOINTS ---


@app.get("/verify-carrier/{mc_number}")
def verify_carrier(mc_number: str):
    api_key = os.getenv("FMCSA_KEY")
    
    # La URL oficial corregida con "webKey"
    url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={api_key}"
    
    # El disfraz de navegador
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Esto hará saltar el error si hay un 403
        data = response.json()
        
        if "content" in data and data["content"]:
            carrier = data["content"][0]["carrier"]
            status = carrier.get("statusCode", "")
            allowed = carrier.get("allowedToOperate", "N")
            
            # El gobierno usa statusCode 'A' para Activo y allowedToOperate 'Y' para Yes
            if status == "A" or allowed == "Y":
                return {"valid": True, "name": carrier.get("legalName"), "status": "Active"}
                
        return {"valid": False, "message": "Carrier not authorized or inactive."}
        
    except Exception as e:
        # Si Railway choca contra el muro, HappyRobot nos mostrará este mensaje exacto
        return {"valid": False, "message": f"Fallo desde Railway: {str(e)}"}

@app.get("/get-loads")
def get_loads(origin: str, equipment: Optional[str] = None):
    # Filtramos por ciudad (ignorando mayúsculas)
    results = [l for l in load_board if origin.lower() in l["origin"].lower()]
    
    if equipment:
        results = [l for l in results if equipment.lower() in l["equipment_type"].lower()]
    
    if not results:
        raise HTTPException(status_code=404, detail="No loads found for this criteria.")
    
    return results

#------------------------------
# Save call logs
#--------------------------------
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


call_logs = []


class CallSummary(BaseModel):
    load_id: Optional[str] = None
    carrier_name: Optional[str] = None
    mc_number: Optional[str] = None
    initial_rate: Optional[int] = None
    agreed_rate: Optional[int] = None
    call_outcome: str
    carrier_sentiment: str

# 3. Endpoint POST: Para que Laura nos envíe los datos al terminar
@app.post("/log-call")
def log_call(summary: CallSummary):
    log_entry = summary.dict()
    log_entry["timestamp"] = datetime.now().isoformat()
    call_logs.append(log_entry)
    return {"status": "success", "message": "Call logged successfully"}

# 4. Endpoint GET: Para que nuestro Dashboard pueda leer los datos
@app.get("/get-logs")
def get_logs():
    return call_logs
