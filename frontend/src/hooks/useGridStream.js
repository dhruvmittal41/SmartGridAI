import { useState, useEffect } from 'react';

export function useGridStream() {
  const [gridData, setGridData] = useState(null);
  const [gridHistory, setGridHistory] = useState([]); // <-- NEW STATE
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/grid-stream');

    ws.onopen = () => setIsConnected(true);
    
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      
      // 1. Set the single point for the Metrics Panel
      setGridData(payload);
      
      // 2. Accumulate the history for the Chart Panel asynchronously
      setGridHistory((prev) => {
        // Safety check
        if (!payload.raw_metrics) return prev;
        
        const timeStr = new Date(payload.timestamp).toLocaleTimeString('en-GB');
        const newData = [...prev, { time: timeStr, actualPower: payload.raw_metrics.power }];
        return newData.slice(-15); // Keep last 15 ticks
      });
      
      if (payload.ml_analysis?.is_anomaly) {
        console.warn(`🚨 GRID ALERT: ${payload.ml_analysis.status.toUpperCase()} detected on ${payload.meter_id}`);
      }
    };

    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, []);

  // Return the history array alongside the single data point
  return { gridData, gridHistory, isConnected }; 
}