import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";

export default function EnergyChart({ data }) {
  // If no data is passed, use some mock telemetry data for the demo
  const chartData = data || [
    { time: "00:00", energy: 400 },
    { time: "04:00", energy: 300 },
    { time: "08:00", energy: 550 },
    { time: "12:00", energy: 800 },
    { time: "16:00", energy: 750 },
    { time: "20:00", energy: 600 },
    { time: "24:00", energy: 450 },
  ];

  return (
    <div style={{ width: "100%", height: "250px", fontFamily: "'Courier New', monospace" }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          {/* Dark faint grid lines */}
          <CartesianGrid strokeDasharray="3 3" stroke="#1a3320" />
          
          {/* Neon green axes */}
          <XAxis dataKey="time" stroke="#00ff41" tick={{ fill: "#00ff41", fontSize: 12 }} />
          <YAxis stroke="#00ff41" tick={{ fill: "#00ff41", fontSize: 12 }} />
          
          {/* Cyberpunk tooltip */}
          <Tooltip 
            contentStyle={{ 
              backgroundColor: "rgba(0, 20, 0, 0.9)", 
              border: "1px solid #00ff41", 
              color: "#00ff41" 
            }}
            itemStyle={{ color: "#00ffff" }}
          />
          
          {/* Cyan glowing line */}
          <Line
            type="monotone"
            dataKey="energy"
            stroke="#00ffff"
            strokeWidth={2}
            dot={{ fill: "#00ffff", r: 3, strokeWidth: 0 }}
            activeDot={{ r: 6, fill: "#ffb000", stroke: "#000" }} // Turns amber on hover
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}