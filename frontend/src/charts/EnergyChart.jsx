import React from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";

export default function EnergyChart({ gridData, gridHistory }) {
  
  // 1. Loading State
  if (!gridHistory || gridHistory.length === 0) {
    return (
      <div style={{ 
        width: "100%", height: "250px", fontFamily: "'Courier New', monospace", 
        color: "#00ff41", display: "flex", justifyContent: "center", alignItems: "center",
        border: "1px dashed #1a3320", opacity: 0.7
      }}>
        [ AWAITING_TELEMETRY_DATA... ]
      </div>
    );
  }

  // 2. Stitch the future forecast onto the end of the history
  let combinedData = [...gridHistory];
  const lastActual = gridHistory[gridHistory.length - 1];
  
  // Mock forecast fallback
  const generateMockForecast = (currentPower) => {
    return [1, 2, 3, 4, 5].map(i => ({
      step: `+${i}h`,
      predicted_power: parseFloat((currentPower + (Math.random() - 0.5)).toFixed(2))
    }));
  };

  const forecastArray = gridData?.forecast || generateMockForecast(lastActual.actualPower);

  combinedData.push({ time: "NOW", actualPower: lastActual.actualPower, predictedPower: lastActual.actualPower });
  
  forecastArray.forEach(f => {
    combinedData.push({ time: f.step, predictedPower: f.predicted_power });
  });

  // 3. Render
  return (
    <div style={{ width: "100%", height: "250px", fontFamily: "'Courier New', monospace" }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={combinedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a3320" />
          <XAxis dataKey="time" stroke="#00ff41" tick={{ fill: "#00ff41", fontSize: 10 }} />
          <YAxis stroke="#00ff41" tick={{ fill: "#00ff41", fontSize: 12 }} domain={['auto', 'auto']} />
          
          <Tooltip 
            contentStyle={{ backgroundColor: "rgba(0, 20, 0, 0.9)", border: "1px solid #00ff41" }}
            itemStyle={{ color: "#00ffff" }}
          />
          
          <Line
            type="monotone"
            dataKey="actualPower"
            stroke="#00ffff"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false} 
          />
          
          <Line
            type="monotone"
            dataKey="predictedPower"
            stroke="#b026ff" 
            strokeWidth={2}
            strokeDasharray="5 5" 
            dot={{ fill: "#b026ff", r: 3, strokeWidth: 0 }}
            isAnimationActive={false} 
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}