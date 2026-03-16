import React, { useMemo, useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { getCityGrid } from "../data/cityGrid";

// --- 1. Vibrant Glassmorphism Styled Icons ---
const createSubstationIcon = (label, isExpanded) => L.divIcon({
  className: "custom-leaflet-icon",
  html: `
    <div style="
      background: rgba(30, 58, 138, 0.75); 
      color: #00f2fe; 
      padding: 12px 18px; 
      border: 1px solid rgba(0, 242, 254, 0.5); 
      border-radius: 12px;
      text-align: center; 
      box-shadow: 0 0 20px rgba(0, 242, 254, 0.6), inset 0 0 10px rgba(255,255,255,0.2); 
      font-family: 'Inter', system-ui, sans-serif; 
      width: max-content; 
      backdrop-filter: blur(8px); 
      cursor: pointer;
      transition: all 0.3s ease;
    ">
      <div style="font-size: 20px; margin-bottom: 4px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));">⚡</div>
      <div style="font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">${label}</div>
      <div style="font-size: 10px; opacity: 0.8; margin-top: 4px; color: #bae6fd;">[ ${isExpanded ? 'UPLINK ACTIVE' : 'STANDBY'} ]</div>
    </div>
  `,
  iconAnchor: [50, 50],
});

const createTransformerIcon = (label, isExpanded) => L.divIcon({
  className: "custom-leaflet-icon",
  html: `
    <div style="
      background: rgba(88, 28, 135, 0.75); 
      color: #d8b4fe; 
      padding: 8px 12px; 
      border: 1px solid rgba(168, 85, 247, 0.5); 
      border-radius: 8px;
      text-align: center; 
      box-shadow: 0 0 15px rgba(168, 85, 247, 0.5); 
      font-family: 'Inter', system-ui, sans-serif; 
      width: max-content; 
      backdrop-filter: blur(4px);
      cursor: pointer;
    ">
      <div style="font-size: 14px; font-weight: 600;">🔌 ${label}</div>
    </div>
  `,
  iconAnchor: [35, 20],
});

const createMeterIcon = (label) => L.divIcon({
  className: "custom-leaflet-icon",
  html: `
    <div style="
      background: rgba(2, 44, 34, 0.85); 
      color: #2dd4bf; 
      padding: 4px 8px; 
      border: 1px solid rgba(45, 212, 191, 0.4); 
      border-radius: 6px;
      text-align: center; 
      font-family: 'monospace'; 
      font-size: 10px; 
      width: max-content; 
      box-shadow: 0 0 8px rgba(45, 212, 191, 0.4);
    ">
      ● ${label}
    </div>
  `,
  iconAnchor: [20, 10],
});

// --- 2. Main Map Component ---
export default function CityGridMap({ cityId, substationId }) {
  const [time, setTime] = useState(new Date().toISOString());
  const [expandedSubstations, setExpandedSubstations] = useState([]);
  const [expandedTransformers, setExpandedTransformers] = useState([]);

  // Telemetry Clock
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toISOString()), 1000);
    return () => clearInterval(timer);
  }, []);

  const grid = useMemo(() => getCityGrid(cityId), [cityId]);

  // Isolate the specific substation selected by the user
  const targetSubstation = useMemo(() => {
    if (!grid || !grid.substations || grid.substations.length === 0) return null;
    return grid.substations.find(s => s.id === substationId) || grid.substations[0];
  }, [grid, substationId]);

  // Auto-expand the target substation when it loads
  useEffect(() => {
    if (targetSubstation) {
      setExpandedSubstations([targetSubstation.id]);
    }
    setExpandedTransformers([]);
  }, [targetSubstation]);

  const toggleSubstation = (id) => {
    setExpandedSubstations((prev) => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const toggleTransformer = (id) => {
    setExpandedTransformers((prev) => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const lines = useMemo(() => {
    const edgeLines = [];
    if (!grid || !targetSubstation) return edgeLines; // Safety check

    const getCoords = (id) => {
      const item = 
        grid.substations.find(s => s.id === id) || 
        grid.transformers.find(t => t.id === id) || 
        grid.meters.find(m => m.id === id);
      return item ? [item.lat, item.lng] : null;
    };

    // Substation to Transformers (Cyan dashed lines)
    grid.transformers.forEach((tr) => {
      if (expandedSubstations.includes(tr.parent) && tr.parent === targetSubstation.id) {
        const parentCoords = getCoords(tr.parent);
        if (parentCoords && tr.lat) {
          edgeLines.push({
            id: `${tr.parent}-${tr.id}`,
            positions: [parentCoords, [tr.lat, tr.lng]],
            color: "#00f2fe", 
            weight: 2,
            dashArray: "6, 6" 
          });
        }
      }
    });

    // Transformers to Meters (Teal solid lines)
    grid.meters.forEach((m) => {
      const parentTransformer = grid.transformers.find(t => t.id === m.parent);
      if (expandedTransformers.includes(m.parent) && parentTransformer?.parent === targetSubstation.id) {
        const parentCoords = getCoords(m.parent);
        if (parentCoords && m.lat) {
          edgeLines.push({
            id: `${m.parent}-${m.id}`,
            positions: [parentCoords, [m.lat, m.lng]],
            color: "#2dd4bf", 
            weight: 1.5,
            opacity: 0.7 
          });
        }
      }
    });

    return edgeLines;
  }, [grid, expandedSubstations, expandedTransformers, targetSubstation]);

  // Determine the center of the map. 
  // If we have a substation, center on it. If not, use the city center. If no city center, default to India.
  const mapCenter = targetSubstation 
    ? [targetSubstation.lat, targetSubstation.lng] 
    : (grid?.center || [28.6139, 77.2090]);

  // Determine the zoom level. Closer if we have a substation, zoomed out if we are defaulting.
  const mapZoom = targetSubstation ? 14 : (grid?.center ? 11 : 5);

  const styles = {
    wrapper: {
      background: "radial-gradient(circle at top, #1e1e38, #0f172a, #020617)",
      color: "#e2e8f0",
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
      padding: "1.5rem",
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      boxSizing: "border-box",
      gap: "1.5rem"
    },
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "1.2rem 2rem",
      background: "rgba(30, 41, 59, 0.4)",
      backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)",
      border: "1px solid rgba(255, 255, 255, 0.05)",
      borderRadius: "20px",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)"
    },
    mapFrame: {
      flexGrow: 1,
      position: "relative",
      borderRadius: "20px",
      overflow: "hidden", 
      border: "1px solid rgba(96, 165, 250, 0.3)",
      boxShadow: "0 0 30px rgba(0,0,0,0.5), inset 0 0 20px rgba(30, 58, 138, 0.2)",
    }
  };

  return (
    <div style={styles.wrapper}>
      {/* Telemetry Header */}
      <div style={styles.header}>
        <div style={{ fontSize: "1.4rem", fontWeight: "700", background: "linear-gradient(to right, #fff, #93c5fd)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          NODE ISOLATION // {targetSubstation ? targetSubstation.label.toUpperCase() : "AWAITING COORDINATES"}
        </div>
        <div style={{ textAlign: "right", fontSize: "0.95rem", color: "#94a3b8" }}>
          <div style={{ display: "flex", gap: "8px", alignItems: "center", justifyContent: "flex-end", marginBottom: "4px" }}>
            <span style={{ 
              width: "10px", 
              height: "10px", 
              borderRadius: "50%", 
              background: targetSubstation ? "#00f2fe" : "#f59e0b", // Yellow if missing
              boxShadow: targetSubstation ? "0 0 12px #00f2fe" : "0 0 12px #f59e0b" 
            }}></span>
            <span style={{ color: "#f8fafc", fontWeight: "600" }}>
              {targetSubstation ? "LINK ESTABLISHED" : "OFFLINE"}
            </span>
          </div>
          <div style={{ fontFamily: "monospace" }}>SYS_T: {time}</div>
        </div>
      </div>

      <div style={styles.mapFrame}>
        <MapContainer 
          key={`${cityId}-${targetSubstation?.id || 'default'}`} 
          center={mapCenter} 
          zoom={mapZoom} 
          style={{ height: "100%", width: "100%", zIndex: 0, backgroundColor: "#020617" }}
          zoomControl={true}
        >
          {/* CartoDB Dark Matter Base Map */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Lines */}
          {lines.map((line) => (
            <Polyline 
              key={line.id} 
              positions={line.positions} 
              pathOptions={{ color: line.color, weight: line.weight, dashArray: line.dashArray, opacity: line.opacity || 1 }} 
            />
          ))}

          {/* Conditional Rendering: Only show markers if targetSubstation exists */}
          {targetSubstation && (
            <>
              <Marker 
                key={targetSubstation.id} 
                position={[targetSubstation.lat, targetSubstation.lng]} 
                icon={createSubstationIcon(targetSubstation.label, expandedSubstations.includes(targetSubstation.id))}
                eventHandlers={{
                  click: () => toggleSubstation(targetSubstation.id),
                }}
              >
                <Popup className="glass-popup">
                  <div style={{ fontFamily: "monospace", color: "#333" }}>
                    <strong>{targetSubstation.label}</strong><br />
                    SYS_LOAD: 85%<br />
                    STATUS: NOMINAL
                  </div>
                </Popup>
              </Marker>

              {/* Transformers */}
              {grid.transformers
                .filter(tr => tr.parent === targetSubstation.id && expandedSubstations.includes(tr.parent))
                .map((tr) => {
                  const isExpanded = expandedTransformers.includes(tr.id);
                  return (
                    <Marker 
                      key={tr.id} 
                      position={[tr.lat, tr.lng]} 
                      icon={createTransformerIcon(tr.label, isExpanded)}
                      eventHandlers={{
                        click: () => toggleTransformer(tr.id),
                      }}
                    >
                      <Popup>
                        <div style={{ fontFamily: "monospace", color: "#333" }}>
                          <strong>{tr.label}</strong><br />
                          NODES_CONNECTED: {grid.meters.filter(m => m.parent === tr.id).length}
                        </div>
                      </Popup>
                    </Marker>
                  );
                })}

              {/* Meters */}
              {grid.meters
                .filter(m => {
                  const parentTr = grid.transformers.find(t => t.id === m.parent);
                  return parentTr && parentTr.parent === targetSubstation.id && expandedTransformers.includes(m.parent);
                })
                .map((m) => (
                  <Marker key={m.id} position={[m.lat, m.lng]} icon={createMeterIcon(m.label)} />
                ))
              }
            </>
          )}
        </MapContainer>
      </div>
    </div>
  );
}