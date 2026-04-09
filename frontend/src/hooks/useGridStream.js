import { useState, useEffect } from 'react';

export function useGridStream() {
  const [gridData, setGridData] = useState(null);
  const [gridHistory, setGridHistory] = useState([]); 
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/grid-stream');

    ws.onopen = () => setIsConnected(true);
    
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      
      const rawAnomaly = payload.ml_analysis?.is_anomaly;
      const isAnomaly = rawAnomaly === true || rawAnomaly === "true" || rawAnomaly === 1;

      if (isAnomaly) {
        console.warn(`🚨 GRID ALERT: ${payload.ml_analysis?.status?.toUpperCase()} detected on ${payload.meter_id}`);
      }
 
      setGridData(payload);
      
      setGridHistory((prev) => {
        if (!payload.raw_metrics) return prev;
        
        const timeStr = new Date(payload.timestamp).toLocaleTimeString('en-GB');
        const newData = [...prev, { time: timeStr, actualPower: payload.raw_metrics.power }];
        return newData.slice(-15); 
      });
    };
    
    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, []);

  return { gridData, gridHistory, isConnected }; 
}