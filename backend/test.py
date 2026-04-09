from firebase_service import write_alert,init_app

init_app()


from firebase_service import send_fcm_push

send_fcm_push(
    title="⚠️ Grid Alert",
    body="Critical voltage detected!",
    data_dict={"type": "voltage", "severity": "CRITICAL"}
)