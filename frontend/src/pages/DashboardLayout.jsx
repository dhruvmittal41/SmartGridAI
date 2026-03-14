import React, { useState } from "react";
import CityGridMap from "../components/CityGrid.jsx"; // Ensure this path is correct
import EnergyChart from "../charts/EnergyChart";
import MetricsPanel from "../components/MetricsPanel";
import AlertsPanel from "../components/AlertsPanel";

export default function DashboardLayout() {
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [cityId, setCityId] = useState("aligarh"); // Default city

  const styles = {
    container: {
      display: "flex",
      width: "100vw",
      height: "100vh",
      backgroundColor: "#050505",
      color: "#00ff41",
      fontFamily: "'Courier New', Courier, monospace",
      overflow: "hidden"
    },
    mapSection: {
      width: isFullScreen ? "0%" : "50%",
      height: "100%",
      transition: "width 0.4s ease-in-out",
      opacity: isFullScreen ? 0 : 1, // Fades out the map when shrinking
      visibility: isFullScreen ? "hidden" : "visible",
    },
    dashboardSection: {
      width: isFullScreen ? "100%" : "50%",
      height: "100%",
      transition: "width 0.4s ease-in-out",
      display: "flex",
      flexDirection: "column",
      padding: "1rem",
      boxSizing: "border-box",
      borderLeft: isFullScreen ? "none" : "1px solid #1a1a1a",
    },
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      borderBottom: "1px solid #00ff41",
      paddingBottom: "10px",
      marginBottom: "20px",
    },
    button: {
      backgroundColor: "transparent",
      color: "#00ffff",
      border: "1px solid #00ffff",
      padding: "5px 15px",
      fontFamily: "inherit",
      cursor: "pointer",
      textTransform: "uppercase",
      letterSpacing: "1px",
      transition: "all 0.2s"
    },
    select: {
      backgroundColor: "#000",
      color: "#00ff41",
      border: "1px solid #00ff41",
      padding: "5px",
      fontFamily: "inherit",
      marginLeft: "10px",
      outline: "none"
    }
  };

  return (
    <div style={styles.container}>
      
      {/* LEFT HALF: Map */}
      <div style={styles.mapSection}>
        {/* Pass the cityId state to the map */}
        <CityGridMap cityId={cityId} /> 
      </div>

      {/* RIGHT HALF: Dashboard */}
      <div style={styles.dashboardSection}>
        
        {/* Dashboard Header & Controls */}
        <div style={styles.header}>
          <div style={{ fontSize: "1.2rem", fontWeight: "bold" }}>
            ▤ TELEMETRY_DATA
            
            {/* City Selector Dropdown */}
            {!isFullScreen && (
              <select 
                style={styles.select} 
                value={cityId} 
                onChange={(e) => setCityId(e.target.value)}
              >
                <option value="aligarh">ALIGARH</option>
                <option value="delhi">NEW DELHI</option>
                <option value="bangalore">BANGALORE</option>
                <option value="mumbai">MUMBAI</option>
                <option value="chennai">CHENNAI</option>
              </select>
            )}
          </div>

          <button 
            style={styles.button}
            onClick={() => setIsFullScreen(!isFullScreen)}
            onMouseOver={(e) => { e.target.style.backgroundColor = 'rgba(0, 255, 255, 0.2)'; }}
            onMouseOut={(e) => { e.target.style.backgroundColor = 'transparent'; }}
          >
            {isFullScreen ? "[ RESTORE_VIEW ]" : "[ FULL_SCREEN ]"}
          </button>
        </div>

        {/* Dashboard Content */}
        <MetricsPanel />
        
        <div style={{ marginBottom: "20px", border: "1px solid #333", padding: "10px", backgroundColor: "#0a0a0a" }}>
           <div style={{ fontSize: "0.8rem", opacity: 0.7, marginBottom: "10px" }}> GRID_POWER_CONSUMPTION (kW)</div>
           <EnergyChart />
        </div>

        <AlertsPanel />

      </div>
    </div>
  );
}