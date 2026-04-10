from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.services.firebase_service import init_firebase, write_alert, send_notification

active_connections = []

app = FastAPI()

init_firebase()

# ✅ Allow all origins (hackathon shortcut)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check
@app.get("/health")
def health():
    return {"status": "OK"}

# ✅ REST API for prediction
@app.post("/api/predict")
async def predict(data: dict):

    values = list(data.values())
    prediction = sum(values) / len(values)

    overload = prediction > 130
    suggestion = "Reduce load immediately" if overload else "System normal"

    # 🔥 Alert object
    alert = {
        "fault_type": "overload" if overload else "normal",
        "severity": "high" if overload else "low",
        "location": "substation_1",
        "load_pct": float(prediction),
        "suggestion": [suggestion]
    }

    # Save to Firebase
    saved_alert = write_alert(alert)

    # Send notification
    send_notification(
        title="⚠️ Grid Alert",
        body=suggestion,
        data_dict=saved_alert
    )

    shap_reasons = []

    if values[0] > 140:
        shap_reasons.append("High load detected")

    if len(values) > 2 and values[2] > 80:
        shap_reasons.append("High temperature")

    if not shap_reasons:
        shap_reasons.append("Normal conditions")

    await broadcast_alert(f"⚠️ {suggestion} | Load: {prediction}")

    return {
        "prediction": float(prediction),
        "overload": overload,
        "suggestion": suggestion,
        "shap_reasons": shap_reasons
    }


# ✅ WebSocket for real-time grid updates
@app.websocket("/ws/grid")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)


async def broadcast_alert(message: str):
    for connection in active_connections:
        await connection.send_text(message)



from app.services.suggestion_engine import get_suggestions


@app.get("/test-suggestions")
def test():
    return get_suggestions(
        fault_type="transformer_overload",
        load_pct=90,
        winding_temp=115,
        hour_of_day=14
    )



from app.services.alert_router import classify_severity, should_send_alert


@app.get("/test-alert")
def test_alert():

    severity = classify_severity(
        fault_label=0,
        confidence=0.6,
        winding_temp=90,
        load_pct=95
    )

    send = should_send_alert("transformer_overload")

    return {
        "severity": severity,
        "should_send": send
    }

from app.services.firebase_service import init_firebase

@app.on_event("startup")
def startup_event():
    init_firebase()


from app.services.firebase_service import write_alert, send_notification

@app.get("/test-firebase")
def test_firebase():

    alert = {
        "fault_type": "transformer_overload",
        "severity": "CRITICAL",
        "load_pct": 110,
        "winding_temp": 125,
        "location": "Substation A"
    }

    db_response = write_alert(alert)

    push_response = send_notification(
        title="⚠️ Critical Alert",
        body="Transformer overload detected",
        data_dict=alert
    )

    return {
        "db": db_response,
        "push": push_response
    }