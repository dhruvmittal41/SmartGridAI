import asyncio
import datetime
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ml_service import GridPredictor

from firebase_service import init_app



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor = GridPredictor()


class GridInput(BaseModel):
    timestamp: str
    meter_id: str
    voltage: float
    current: float
    frequency: float
    energy_kwh: float

@app.on_event("startup")
async def startup_event():
    init_app()

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Grid service running 🚀"}


@app.post("/api/predict")
async def predict(data: GridInput):
    result = predictor.predict(data.model_dump())
    return result


@app.websocket("/ws/grid")
async def grid_data_stream(websocket: WebSocket):
    await websocket.accept()
    print("Frontend client connected to grid stream!")

    fault_duration_remaining = 0
    current_fault_voltage = None

    try:
        while True:
            frequency = random.normalvariate(50.0, 0.05)
            is_simulated_fault = False

            if fault_duration_remaining > 0:
                voltage = current_fault_voltage
                fault_duration_remaining -= 1
                is_simulated_fault = True
            else:
                if random.random() < 0.05:
                    current_fault_voltage = random.choice([180.0, 275.0])
                    voltage = current_fault_voltage
                    fault_duration_remaining = 5
                    is_simulated_fault = True
                    print(f"⚠️ FAULT INJECTED: {voltage}V")
                else:
                    voltage = random.normalvariate(230.0, 1.0)

            raw_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "meter_id": "M1-MAIN",
                "voltage": voltage,
                "current": random.normalvariate(0.1, 0.05),
                "frequency": frequency,
                "energy_kwh": random.normalvariate(0.005, 0.001),
            }

            processed_payload = predictor.predict(raw_data)


            if is_simulated_fault:
                if "ml_analysis" not in processed_payload:
                    processed_payload["ml_analysis"] = {}

                processed_payload["ml_analysis"]["is_anomaly"] = True
                processed_payload["ml_analysis"]["status"] = "CRITICAL VOLTAGE"

            await websocket.send_json(processed_payload)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print("Frontend client disconnected.")