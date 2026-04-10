import firebase_admin
from firebase_admin import credentials, firestore, messaging
import datetime
import uuid

db = None

def init_firebase():
    global db

    if not firebase_admin._apps:
        cred = credentials.Certificate("credentials/serviceAccountKey.json")
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    print("🔥 Firebase initialized")

def write_alert(alert_dict):
    global db

    alert_id = str(uuid.uuid4())

    alert_data = {
        "alert_id": alert_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "fault_type": alert_dict.get("fault_type"),
        "severity": alert_dict.get("severity"),
        "location": alert_dict.get("location"),
        "load_pct": alert_dict.get("load_pct"),
        "suggestion": alert_dict.get("suggestion", []),
        "acknowledged": False,
        "acknowledged_by": None,
        "acknowledged_at": None,
    }

    db.collection("alerts").document(alert_id).set(alert_data)

    print(f"✅ Alert saved: {alert_id}")
    return alert_data


def send_notification(title, body, data_dict):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data={k: str(v) for k, v in data_dict.items()},
        topic="substations",
    )

    response = messaging.send(message)
    print(f"📲 Notification sent: {response}")
    return response