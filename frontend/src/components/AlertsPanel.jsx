import React, { useState, useEffect } from "react";

export default function AlertsPanel({ gridData }) {
  const [logs, setLogs] = useState([
    { time: new Date().toLocaleTimeString('en-GB'), type: "INFO", msg: "Uplink established. Awaiting telemetry..." }
  ]);

  useEffect(() => {
    if (!gridData) return;

    const { ml_analysis, meter_id, raw_metrics } = gridData;
    const now = new Date().toLocaleTimeString('en-GB');

    // If the LSTM caught something, log an ERR or WARN
    if (ml_analysis.is_anomaly && ml_analysis.status !== "normal") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLogs(prev => [
        { 
          time: now, 
          type: "ERR", 
          msg: `CRITICAL: ${ml_analysis.status.toUpperCase()} detected at ${meter_id}. Volts: ${raw_metrics.voltage}V` 
        },
        ...prev
      ].slice(0, 50)); // Keep only the last 50 logs so the browser doesn't crash
    } 
    // Just to keep the console looking alive, log a routine ping every 10 messages
    else if (Math.random() > 0.9) { 
      setLogs(prev => [
        { time: now, type: "INFO", msg: `Routine ping: ${meter_id} nominal.` },
        ...prev
      ].slice(0, 50));
    }
  }, [gridData]);

  const getColor = (type) => {
    if (type === "ERR") return "#ff003c"; 
    if (type === "WARN") return "#ffb000"; 
    return "#00ffff"; 
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
            <span style={{ color: getColor(log.type) }}>{log.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}