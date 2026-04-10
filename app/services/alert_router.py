from datetime import datetime, timedelta

# last alerts store karne ke liye (deduplication)
last_alerts = {}


def classify_severity(
    fault_label: int,
    confidence: float,
    winding_temp: float,
    load_pct: float
) -> str:

    # 🔴 CRITICAL
    if fault_label > 0 and (
        confidence > 0.85 or
        winding_temp > 120 or
        load_pct > 110
    ):
        return "CRITICAL"

    # 🟠 HIGH
    elif fault_label > 0 and confidence > 0.70:
        return "HIGH"

    # 🟡 MEDIUM
    elif fault_label > 0:
        return "MEDIUM"

    # 🟢 LOW
    else:
        return "LOW"


# 🧠 Deduplication logic (5 min rule)
def should_send_alert(fault_type: str) -> bool:
    now = datetime.now()

    if fault_type in last_alerts:
        last_time = last_alerts[fault_type]

        # agar 5 min ke andar same alert aya → skip
        if now - last_time < timedelta(minutes=5):
            return False

    # update time
    last_alerts[fault_type] = now
    return True