import firebase_admin
from firebase_admin import credentials, firestore, messaging
import datetime
import uuid


db = None


def init_app():
    global db

    if not firebase_admin._apps:
        cred = credentials.Certificate("credentials/serviceAccountKey.json")
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    print("🔥 Firebase initialized successfully")
    print("DB object:", db) 



def write_alert(alert_dict):
    global db

    alert_id = str(uuid.uuid4())

    alert_data = {
        "alert_id": alert_id,
        "timestamp": alert_dict.get("timestamp", datetime.datetime.utcnow().isoformat()),
        "fault_type": alert_dict.get("fault_type"),
        "fault_label": alert_dict.get("fault_label"),
        "severity": alert_dict.get("severity"),
        "location": alert_dict.get("location"),
        "shap_reasons": alert_dict.get("shap_reasons", []),
        "suggestion": alert_dict.get("suggestion", []),
        "sub_score": alert_dict.get("sub_score"),
        "trans_score": alert_dict.get("trans_score"),
        "meter_score": alert_dict.get("meter_score"),
        "winding_temp_C": alert_dict.get("winding_temp_C"),
        "load_pct": alert_dict.get("load_pct"),
        "loss_ratio": alert_dict.get("loss_ratio"),
        "acknowledged": False,
        "acknowledged_by": None,
        "acknowledged_at": None,
    }

    db.collection("alerts").document(alert_id).set(alert_data)

    print(f"✅ Alert written: {alert_id}")
    return alert_data



def send_fcm_push(title, body, data_dict):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data={k: str(v) for k, v in data_dict.items()},
        topic="substations",
    )

    response = messaging.send(message)
    print(f"📲 FCM sent: {response}")

    return response