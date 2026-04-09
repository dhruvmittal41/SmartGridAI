import React from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";

export default function EnergyChart({ gridData, gridHistory }) {
  
  // Theme Variables
  const textColor = "#e2e8f0";
  const subtextColor = "#94a3b8";
  const actualLineColor = "#00f2fe"; // Electric blue for actual data
  const predictedLineColor = "#c084fc"; // Soft purple for predicted data

  // 1. Loading State (Glassmorphism Style)
  if (!gridHistory || gridHistory.length === 0) {
    return (
      <div style={{ 
        width: "100%", height: "250px", 
        fontFamily: "system-ui, -apple-system, sans-serif", 
        color: subtextColor, display: "flex", justifyContent: "center", alignItems: "center",
        background: "rgba(15, 23, 42, 0.3)", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)"
      }}>
        Awaiting Telemetry Data...
      </div>
    );
  }

  // 2. Stitch the future forecast onto the end of the history
  let combinedData = [...gridHistory];
  const lastActual = gridHistory[gridHistory.length - 1];
  
  // Safely grab the current power value
  const currentPower = lastActual.actualPower || 0;
  
  // Mock forecast fallback using Power (ensuring no negative values)
  const generateMockForecast = (currentVal) => {
    return [1, 2, 3, 4, 5].map(i => {
      // +/- 5% fluctuation from the current value to keep it realistic
      const fluctuation = currentVal * (Math.random() * 0.1 - 0.05); 
      let predictedVal = currentVal + fluctuation;
      
      // Power cannot be negative
      if (predictedVal < 0) predictedVal = 0; 

      return {
        step: `+${i}h`,
        predicted_power: parseFloat(predictedVal.toFixed(2))
      };
    });
  };

  const forecastArray = gridData?.forecast || generateMockForecast(currentPower);

  // Connect the lines seamlessly at the "NOW" junction
  combinedData.push({ 
    time: "NOW", 
    actualPower: currentPower, 
    predictedPower: currentPower 
  });
  
  forecastArray.forEach(f => {
    combinedData.push({ 
      time: f.step, 
      predictedPower: f.predicted_power || f.predictedPower 
    });
  });

  // 3. Render Chart
  return (
    <div style={{ width: "100%", height: "250px", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={combinedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          {/* Subtle horizontal grid lines only */}
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.08)" vertical={false} />
          
          <XAxis 
            dataKey="time" 
            stroke="transparent" 
            tick={{ fill: subtextColor, fontSize: 12 }} 
            dy={10} 
          />
          <YAxis 
            stroke="transparent" 
            tick={{ fill: subtextColor, fontSize: 12 }} 
            domain={['auto', 'auto']} 
            dx={-10} 
          />
          
          {/* Glassmorphic Tooltip */}
          <Tooltip 
            contentStyle={{ 
              backgroundColor: "rgba(15, 23, 42, 0.8)", 
              backdropFilter: "blur(12px)",
              WebkitBackdropFilter: "blur(12px)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "8px",
              color: textColor
            }}
            itemStyle={{ color: textColor, fontWeight: "500" }}
            labelStyle={{ color: subtextColor, marginBottom: "4px" }}
          />
          
          {/* Actual Power Line */}
          <Line
            name="Actual Power (kW)"
            type="monotone"
            dataKey="actualPower"
            stroke={actualLineColor}
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 6, fill: actualLineColor, stroke: "#0f172a", strokeWidth: 2 }}
            isAnimationActive={true} 
          />
          
          {/* Predicted Power Line */}
          <Line
            name="Predicted Power (kW)"
            type="monotone"
            dataKey="predictedPower"
            stroke={predictedLineColor} 
            strokeWidth={3}
            strokeDasharray="5 5" 
            dot={{ fill: predictedLineColor, r: 4, strokeWidth: 0 }}
            activeDot={{ r: 6, fill: predictedLineColor, stroke: "#0f172a", strokeWidth: 2 }}
            isAnimationActive={true} 
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}