from fastapi import FastAPI, HTTPException
from typing import Optional

app = FastAPI()

# Tu base de datos de cargas (Objetivo 1)
load_db = [
    {"load_id": "ES01", "origin": "Madrid", "destination": "Barcelona", "loadboard_rate": 850, "equipment_type": "Lona", "weight": "24,000 kg"},
    {"load_id": "ES02", "origin": "Valencia", "destination": "Sevilla", "loadboard_rate": 720, "equipment_type": "Frigorífico", "weight": "20,000 kg"},
    {"load_id": "ES03", "origin": "Bilbao", "destination": "Madrid", "loadboard_rate": 550, "equipment_type": "Lona", "weight": "24,000 kg"},
    {"load_id": "ES04", "origin": "Zaragoza", "destination": "Málaga", "loadboard_rate": 980, "equipment_type": "Lona", "weight": "22,000 kg"},
    {"load_id": "ES05", "origin": "Murcia", "destination": "Perpiñán", "loadboard_rate": 1100, "equipment_type": "Frigorífico", "weight": "18,000 kg"},
    {"load_id": "ES06", "origin": "Valladolid", "destination": "Vigo", "loadboard_rate": 600, "equipment_type": "Cisterna", "weight": "25,000 kg"},
    {"load_id": "ES07", "origin": "Barcelona", "destination": "Valencia", "loadboard_rate": 450, "equipment_type": "Lona", "weight": "12,000 kg"},
    {"load_id": "ES08", "origin": "Sevilla", "destination": "Lisboa", "loadboard_rate": 800, "equipment_type": "Lona", "weight": "20,000 kg"},
    {"load_id": "ES09", "origin": "Gijón", "destination": "Santander", "loadboard_rate": 300, "equipment_type": "Caja abierta", "weight": "5,000 kg"},
    {"load_id": "ES10", "origin": "Alicante", "destination": "Madrid", "loadboard_rate": 650, "equipment_type": "Lona", "weight": "24,000 kg"}
]

@app.get("/")
def home():
    return {"status": "Acme Logistics API is running"}

@app.get("/get-load")
def get_load(origin: str):
    # Busca la carga que coincida con el origen que diga el camionero
    load = next((l for l in load_db if origin.lower() in l["origin"].lower()), None)
    if load:
        return load
    raise HTTPException(status_code=404, detail="No loads found for this location")