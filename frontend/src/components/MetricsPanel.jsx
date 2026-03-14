import React from "react";

export default function MetricsPanel() {
  const metrics = [
    { label: "VOLTAGE", value: "250 V", color: "#00ff41" },
    { label: "CURRENT", value: " 0.15 A", color: "#00ffff" },
    { label: "POWER_CONSUMPTION", value: "0.03 kWh", color: "#ffb000" },
    { label: "FREQUENCY", value: "50.02 Hz", color: "#00ffff" },
    { label: "ACTIVE_METERS", value: "10", color: "#00ff41" },
    { label: "CRIT_ALERTS", value: "0", color: "#ffb000" }
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "20px" }}>
      {metrics.map((m, idx) => (
        <div 
          key={idx} 
          style={{ 
            border: `1px solid ${m.color}`, 
            backgroundColor: "rgba(0, 20, 0, 0.4)", 
            padding: "15px", 
            textAlign: "center" 
          }}
        >
          <div style={{ fontSize: "0.8rem", opacity: 0.7, marginBottom: "5px" }}>{m.label}</div>
          <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: m.color }}>{m.value}</div>
        </div>
      ))}
    </div>
  );
}