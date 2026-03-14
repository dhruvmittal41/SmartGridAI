import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import SubstationNodes from "./SubstationNodes";
import PowerLines from "./PowerLines.jsx";


export default function GridMap() {
  // A simple clock for the telemetry header
  const [time, setTime] = useState(new Date().toISOString());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toISOString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // --- CCSDS Dashboard Styles ---
  const styles = {
    wrapper: {
      backgroundColor: "#050505", // Deep space black
      color: "#00ff41",           // Terminal phosphor green
      fontFamily: "'Courier New', Courier, monospace",
      padding: "1rem",
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      boxSizing: "border-box",
      border: "1px solid #1a1a1a",
    },
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      borderBottom: "2px solid #00ff41",
      paddingBottom: "10px",
      marginBottom: "15px",
      textTransform: "uppercase",
      letterSpacing: "2px",
    },
    title: {
      fontSize: "1.2rem",
      fontWeight: "bold",
    },
    telemetry: {
      fontSize: "0.85rem",
      opacity: 0.8,
      textAlign: "right",
    },
    mapFrame: {
      flexGrow: 1,
      position: "relative",
      border: "1px solid #333",
      boxShadow: "0 0 15px rgba(0, 255, 65, 0.1)", // Slight green glow around the map
    },
    footer: {
      marginTop: "10px",
      fontSize: "0.75rem",
      display: "flex",
      justifyContent: "space-between",
      opacity: 0.7,
    }
  };

  return (
    <div style={styles.wrapper}>
      {/* --- Dashboard Header --- */}
      <div style={styles.header}>
        <div style={styles.title}>
          ▤ SYS_MONITOR // REGIONAL_GRID_LINK
        </div>
        <div style={styles.telemetry}>
          <div>STATUS: <span style={{color: "#00ff41"}}>ONLINE</span></div>
          <div>SYS_T: {time}</div>
        </div>
      </div>

      {/* --- Map Container Frame --- */}
      <div style={styles.mapFrame}>
        <MapContainer
          center={[22.5, 78.9]}
          zoom={5}
          style={{ height: "100%", width: "100%", backgroundColor: "#000" }}
          zoomControl={false} // Hides the default bright white +/- buttons for a cleaner look
        >
          {/* CartoDB Dark Matter Base Map */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          <SubstationNodes />
          <PowerLines />

        </MapContainer>
      </div>

      {/* --- Dashboard Footer --- */}
      <div style={styles.footer}>
        <span>LAT: 22.5000 // LNG: 78.9000 // UPLINK: SECURE</span>
       
      </div>
    </div>
  );
}