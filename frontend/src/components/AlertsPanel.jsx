import React from "react";

export default function AlertsPanel() {
  const logs = [
    { time: "18:29:42", type: "INFO", msg: "Uplink established." },
    { time: "18:28:15", type: "WARN", msg: "Voltage drop detected at S1-T2." },
    { time: "18:25:00", type: "INFO", msg: "Routine ping: All nodes nominal." },
    { time: "18:12:04", type: "ERR", msg: "Comm failure at Meter M41. Retrying..." },
    { time: "18:12:06", type: "INFO", msg: "Comm restored at Meter M41." },
    { time: "17:59:22", type: "INFO", msg: "Grid frequency stable at 50.02Hz." },
  ];

  const getColor = (type) => {
    if (type === "ERR") return "#ff003c"; // Red
    if (type === "WARN") return "#ffb000"; // Amber
    return "#00ffff"; // Cyan for INFO
  };

  return (
    <div style={{ 
      border: "1px solid #333", 
      backgroundColor: "#000", 
      flexGrow: 1, 
      display: "flex", 
      flexDirection: "column",
      overflow: "hidden" 
    }}>
      <div style={{ borderBottom: "1px solid #333", padding: "5px 10px", fontSize: "0.8rem", backgroundColor: "#0a0a0a" }}>
         SYS_LOGS // RECENT_EVENTS
      </div>
      <div style={{ padding: "10px", overflowY: "auto", flexGrow: 1, fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "8px" }}>
        {logs.map((log, idx) => (
          <div key={idx} style={{ display: "flex", gap: "10px" }}>
            <span style={{ opacity: 0.5 }}>[{log.time}]</span>
            <span style={{ color: getColor(log.type), width: "40px" }}>{log.type}</span>
            <span style={{ color: "#00ff41" }}>{log.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}