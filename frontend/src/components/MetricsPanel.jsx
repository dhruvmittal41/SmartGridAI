import React from "react";

export default function MetricsPanel({ gridData }) {
 
  const raw = gridData?.raw_metrics || { voltage: 0, current: 0, energy_kwh: 0, frequency: 0 };
  const ml = gridData?.ml_analysis || { status: "AWAITING_DATA", is_anomaly: false };

 
  const isDanger = ml.is_anomaly && ml.status !== "normal";
  const mainColor = isDanger ? "#ff003c" : "#00ff41";

  const metrics = [
    { label: "VOLTAGE", value: `${raw.voltage.toFixed(2)} V`, color: isDanger ? "#ff003c" : "#00ff41" },
    { label: "CURRENT", value: `${raw.current.toFixed(2)} A`, color: "#00ffff" },
    { label: "E_KWH", value: `${raw.energy_kwh?.toFixed(4)} kWh`, color: "#00ffff" },
    { label: "FREQUENCY", value: `${raw.frequency.toFixed(2)} Hz`, color: "#00ffff" },
    { label: "SYS_STATUS", value: ml.status.toUpperCase(), color: mainColor },
    { label: "ACTIVE_METERS", value: gridData ? "1" : "0", color: "#00ff41" }
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
            textAlign: "center",
            transition: "all 0.3s ease"
          }}
        >
          <div style={{ fontSize: "0.8rem", opacity: 0.7, marginBottom: "5px" }}>{m.label}</div>
          <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: m.color }}>{m.value}</div>
        </div>
      ))}
    </div>
  );
}