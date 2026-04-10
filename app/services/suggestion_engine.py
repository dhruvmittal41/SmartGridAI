from typing import List, Dict


def get_suggestions(
    fault_type: str,
    load_pct: float,
    winding_temp: float,
    hour_of_day: int
) -> List[Dict]:

    suggestions = []

    # 🔴 1. FEEDER OVERLOAD
    if fault_type == "feeder_overload":
        if load_pct > 100:
            suggestions.append({
                "action": "Immediate load shedding required",
                "priority": "HIGH",
                "estimated_impact": "Prevents feeder failure and blackout",
                "time_to_implement": "Immediate"
            })
        elif load_pct > 90:
            suggestions.append({
                "action": "Rebalance load to alternate feeder",
                "priority": "MEDIUM",
                "estimated_impact": "Reduces overload stress",
                "time_to_implement": "15-30 minutes"
            })

    # 🔴 2. TRANSFORMER OVERLOAD
    elif fault_type == "transformer_overload":
        if winding_temp > 110:
            suggestions.append({
                "action": "Reduce transformer load immediately",
                "priority": "HIGH",
                "estimated_impact": "Prevents transformer damage",
                "time_to_implement": "Immediate"
            })
        elif load_pct > 85:
            suggestions.append({
                "action": "Schedule maintenance within 48 hours",
                "priority": "MEDIUM",
                "estimated_impact": "Avoids future overload failure",
                "time_to_implement": "24-48 hours"
            })

    # 🔴 3. VOLTAGE SAG
    elif fault_type == "voltage_sag":
        suggestions.append({
            "action": "Check reactive power compensation",
            "priority": "MEDIUM",
            "estimated_impact": "Improves voltage stability",
            "time_to_implement": "30-60 minutes"
        })
        suggestions.append({
            "action": "Activate capacitor bank switching",
            "priority": "MEDIUM",
            "estimated_impact": "Restores voltage levels",
            "time_to_implement": "Immediate"
        })

    # 🔴 4. ENERGY THEFT
    elif fault_type == "energy_theft":
        suggestions.append({
            "action": "Flag meter ID for inspection",
            "priority": "HIGH",
            "estimated_impact": "Prevents revenue loss",
            "time_to_implement": "Within 24 hours"
        })
        suggestions.append({
            "action": "Trigger billing audit",
            "priority": "MEDIUM",
            "estimated_impact": "Identifies irregular consumption",
            "time_to_implement": "24 hours"
        })

    # 🔴 5. UNDERVOLTAGE
    elif fault_type == "undervoltage":
        suggestions.append({
            "action": "Check feeder end loads",
            "priority": "MEDIUM",
            "estimated_impact": "Identifies voltage drop cause",
            "time_to_implement": "30-60 minutes"
        })
        suggestions.append({
            "action": "Adjust voltage regulator tap settings",
            "priority": "MEDIUM",
            "estimated_impact": "Stabilizes voltage",
            "time_to_implement": "15 minutes"
        })

    # 🟢 Default case
    else:
        suggestions.append({
            "action": "No major issue detected",
            "priority": "LOW",
            "estimated_impact": "System stable",
            "time_to_implement": "N/A"
        })

    return suggestions