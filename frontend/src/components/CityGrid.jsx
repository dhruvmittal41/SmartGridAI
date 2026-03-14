import React, { useMemo, useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { getCityGrid } from "../data/cityGrid";

// --- 1. CCSDS Mission Control Styled Icons ---
// Added 'isExpanded' parameter and cursor pointer
const createSubstationIcon = (label, isExpanded) => L.divIcon({
  className: "custom-leaflet-icon",
  html: `
    <div style="background: rgba(0, 20, 40, 0.85); color: #00ffff; padding: 10px 14px; border: 1px solid #00ffff; text-align: center; box-shadow: 0 0 10px rgba(0, 255, 255, 0.4); font-family: 'Courier New', monospace; width: max-content; backdrop-filter: blur(2px); cursor: pointer;">
      <div style="font-size: 16px; margin-bottom: 2px;">[ ${isExpanded ? '-' : '+'} ] 🏭</div>
      <div style="font-weight: bold; letter-spacing: 1px; text-transform: uppercase;">${label}</div>
      <div style="font-size: 10px; opacity: 0.7;">SYS_HUB // PRI_PWR</div>
    </div>
  `,
  iconAnchor: [50, 50],
});

const createTransformerIcon = (label, isExpanded) => L.divIcon({
  className: "custom-leaflet-icon",
  html: `
    <div style="background: rgba(40, 20, 0, 0.85); color: #ffb000; padding: 6px 10px; border: 1px solid #ffb000; text-align: center; box-shadow: 0 0 8px rgba(255, 176, 0, 0.4); font-family: 'Courier New', monospace; width: max-content; cursor: pointer;">
      <div style="font-size: 14px;">[ ${isExpanded ? '-' : '+'} ] ${label}</div>
    </div>
  `,
  iconAnchor: [35, 20],
});

const createMeterIcon = (label) => L.divIcon({
  className: "custom-leaflet-icon",
  html: `
    <div style="background: rgba(0, 20, 0, 0.85); color: #00ff41; padding: 3px 6px; border: 1px solid #00ff41; text-align: center; font-family: 'Courier New', monospace; font-size: 9px; width: max-content; box-shadow: 0 0 5px rgba(0, 255, 65, 0.3);">
      > ${label}
    </div>
  `,
  iconAnchor: [20, 10],
});

// --- 2. Main Map Component ---
export default function CityGridMap({ cityId }) {
  // Telemetry Clock
  const [time, setTime] = useState(new Date().toISOString());
  
  // Track which nodes are currently clicked/expanded
  const [expandedSubstations, setExpandedSubstations] = useState([]);
  const [expandedTransformers, setExpandedTransformers] = useState([]);

  // Update clock every second
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toISOString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Reset expanded states when the city changes
  useEffect(() => {
  
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExpandedSubstations([]);
   
    setExpandedTransformers([]);
  }, [cityId]);

  const grid = useMemo(() => getCityGrid(cityId), [cityId]);

  // Handle clicking a substation marker
  const toggleSubstation = (substationId) => {
    setExpandedSubstations((prev) => 
      prev.includes(substationId) 
        ? prev.filter(id => id !== substationId) // Collapse if already open
        : [...prev, substationId]                // Expand if closed
    );
  };

  // Handle clicking a transformer marker
  const toggleTransformer = (transformerId) => {
    setExpandedTransformers((prev) => 
      prev.includes(transformerId) 
        ? prev.filter(id => id !== transformerId) // Collapse if already open
        : [...prev, transformerId]                // Expand if closed
    );
  };

  const lines = useMemo(() => {
    const edgeLines = [];
    const getCoords = (id) => {
      const item = 
        grid.substations.find(s => s.id === id) || 
        grid.transformers.find(t => t.id === id) || 
        grid.meters.find(m => m.id === id);
      return item ? [item.lat, item.lng] : null;
    };

    // Substation to Transformers (Cyan lines - visible ONLY if expanded)
    grid.transformers.forEach((tr) => {
      if (expandedSubstations.includes(tr.parent)) {
        const parentCoords = getCoords(tr.parent);
        if (parentCoords && tr.lat) {
          edgeLines.push({
            id: `${tr.parent}-${tr.id}`,
            positions: [parentCoords, [tr.lat, tr.lng]],
            color: "#00ffff", 
            weight: 2,
            dashArray: "5, 5" 
          });
        }
      }
    });

    // Transformers to Meters (Green lines - visible ONLY if expanded)
    grid.meters.forEach((m) => {
      if (expandedTransformers.includes(m.parent)) {
        const parentCoords = getCoords(m.parent);
        if (parentCoords && m.lat) {
          edgeLines.push({
            id: `${m.parent}-${m.id}`,
            positions: [parentCoords, [m.lat, m.lng]],
            color: "#00ff41", 
            weight: 1,
            opacity: 0.6 
          });
        }
      }
    });

    return edgeLines;
  }, [grid, expandedSubstations, expandedTransformers]); // Added both states to dependency array

  // --- CCSDS Dashboard Styles ---
  const styles = {
    wrapper: {
      backgroundColor: "#050505",
      color: "#00ff41",
      fontFamily: "'Courier New', Courier, monospace",
      padding: "1rem",
      height: "90vh",
      display: "flex",
      flexDirection: "column",
      boxSizing: "border-box",
      border: "1px solid #1a1a1a",
    },
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      borderBottom: "1px solid #00ff41",
      paddingBottom: "10px",
      marginBottom: "15px",
    },
    mapFrame: {
      flexGrow: 1,
      position: "relative",
      border: "1px solid #333",
      boxShadow: "inset 0 0 20px rgba(0,0,0,1)", 
    }
  };

  return (
    <div style={styles.wrapper}>
      
      {/* Telemetry Header */}
      <div style={styles.header}>
        <div style={{ fontSize: "1.2rem", fontWeight: "bold" }}>
          ▤ SYS_MONITOR // GRID_UPLINK // {cityId.toUpperCase()}
        </div>
        <div style={{ fontSize: "0.85rem", textAlign: "right", opacity: 0.8 }}>
          <div>STATUS: <span style={{color: "#00ff41"}}>ACTIVE</span></div>
          <div>SYS_T: {time}</div>
        </div>
      </div>

      <div style={styles.mapFrame}>
        <MapContainer 
          key={cityId} 
          center={grid.center} 
          zoom={13} 
          style={{ height: "100%", width: "100%", zIndex: 0, backgroundColor: "#000" }}
          zoomControl={false}
        >
          {/* CartoDB Dark Matter Base Map */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {lines.map((line) => (
            <Polyline 
              key={line.id} 
              positions={line.positions} 
              pathOptions={{ color: line.color, weight: line.weight, dashArray: line.dashArray, opacity: line.opacity || 1 }} 
            />
          ))}

          {/* Substations are always visible */}
          {grid.substations.map((sub) => {
            const isExpanded = expandedSubstations.includes(sub.id);
            return (
              <Marker 
                key={sub.id} 
                position={[sub.lat, sub.lng]} 
                icon={createSubstationIcon(sub.label, isExpanded)}
                eventHandlers={{
                  click: () => toggleSubstation(sub.id),
                }}
              >
                <Popup>
                  <div style={{ fontFamily: "monospace" }}>
                    <strong>{sub.label}</strong><br />
                    SYS_LOAD: 85%<br />
                    STATUS: NOMINAL<br />
                    STATE: {isExpanded ? "EXPANDED" : "COLLAPSED"}
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* Only map through transformers whose parent substation is expanded */}
          {grid.transformers
            .filter(tr => expandedSubstations.includes(tr.parent))
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
                    <div style={{ fontFamily: "monospace" }}>
                      <strong>{tr.label}</strong><br />
                      NODES_CONNECTED: {grid.meters.filter(m => m.parent === tr.id).length}<br />
                      STATE: {isExpanded ? "EXPANDED" : "COLLAPSED"}
                    </div>
                  </Popup>
                </Marker>
              );
            })}

          {/* Only map through meters whose parent transformer is expanded */}
          {grid.meters
            .filter(m => expandedTransformers.includes(m.parent))
            .map((m) => (
              <Marker key={m.id} position={[m.lat, m.lng]} icon={createMeterIcon(m.label)} />
            ))
          }
        </MapContainer>
      </div>
    </div>
  );
}