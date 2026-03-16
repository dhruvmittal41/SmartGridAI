import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom"; 
import CityGridMap from "../components/CityGrid.jsx"; 
import EnergyChart from "../charts/EnergyChart";
import MetricsPanel from "../components/MetricsPanel";
import AlertsPanel from "../components/AlertsPanel";
import { useGridStream } from "../hooks/useGridStream";

export default function DashboardLayout() {
  const { cityId: cityIdFromUrl } = useParams(); 
  const navigate = useNavigate(); 

  const [isFullScreen, setIsFullScreen] = useState(false);
  const [cityId, setCityId] = useState(cityIdFromUrl || "aligarh"); 
  
  // Button hover states for inline styling
  const [hoveredBtn, setHoveredBtn] = useState(null);
  
  useEffect(() => {
    if (cityIdFromUrl) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCityId(cityIdFromUrl);
    }
  }, [cityIdFromUrl]);

  const { gridData, gridHistory, isConnected } = useGridStream();

  // --- GLASSMORPHISM & DARK GRADIENT THEME ---
  const titleColor = "#ffffff"; 
  const textColor = "#e2e8f0";
  const subtextColor = "#94a3b8"; 

  const glassStyle = {
    background: "rgba(30, 41, 59, 0.4)", 
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)", 
    border: "1px solid rgba(255, 255, 255, 0.08)",
    boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.3)",
    borderRadius: "16px",
  };

  const styles = {
    container: { 
      display: "flex", 
      width: "100vw", 
      height: "100vh", 
      background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #0f172a 100%)",
      color: textColor, 
      fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", 
      overflow: "hidden" 
    },
    mapSection: { 
      width: isFullScreen ? "0%" : "50%", 
      height: "100%", 
      transition: "width 0.4s cubic-bezier(0.4, 0, 0.2, 1)", 
      opacity: isFullScreen ? 0 : 1, 
      visibility: isFullScreen ? "hidden" : "visible",
      padding: isFullScreen ? "0" : "1.5rem 0.75rem 1.5rem 1.5rem", // Padding around the map to let the gradient show
      boxSizing: "border-box"
    },
    mapWrapper: {
      width: "100%",
      height: "100%",
      borderRadius: "16px",
      overflow: "hidden", // Ensures the map respects the rounded corners
      boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.3)",
      border: "1px solid rgba(255, 255, 255, 0.08)",
    },
    dashboardSection: { 
      width: isFullScreen ? "100%" : "50%", 
      height: "100%", 
      transition: "width 0.4s cubic-bezier(0.4, 0, 0.2, 1)", 
      display: "flex", 
      flexDirection: "column", 
      padding: isFullScreen ? "1.5rem" : "1.5rem 1.5rem 1.5rem 0.75rem", 
      boxSizing: "border-box", 
      gap: "1.25rem",
      overflowY: "auto"
    },
    header: { 
      ...glassStyle,
      display: "flex", 
      justifyContent: "space-between", 
      alignItems: "center", 
      padding: "1rem 1.5rem", 
    },
    headerLeft: {
      display: "flex",
      alignItems: "center",
      gap: "1rem"
    },
    title: {
      fontSize: "1.25rem",
      fontWeight: "600",
      color: titleColor,
      letterSpacing: "0.5px"
    },
    statusDot: { 
      display: "inline-block", 
      width: "10px", 
      height: "10px", 
      borderRadius: "50%", 
      backgroundColor: isConnected ? "#00f2fe" : "#ef4444", 
      boxShadow: isConnected ? "0 0 10px #00f2fe, 0 0 20px #00f2fe" : "0 0 10px #ef4444",
      transition: "all 0.3s ease"
    },
    select: { 
      backgroundColor: "rgba(15, 23, 42, 0.6)", 
      color: titleColor, 
      border: "1px solid rgba(255, 255, 255, 0.1)", 
      padding: "8px 16px", 
      borderRadius: "8px",
      fontFamily: "inherit", 
      fontSize: "0.95rem",
      outline: "none",
      cursor: "pointer",
      transition: "border-color 0.2s"
    },
    headerRight: {
      display: "flex",
      gap: "10px"
    },
    disconnectBtn: { 
      backgroundColor: hoveredBtn === 'disconnect' ? "rgba(239, 68, 68, 0.15)" : "rgba(15, 23, 42, 0.4)", 
      color: hoveredBtn === 'disconnect' ? "#ef4444" : titleColor, 
      border: `1px solid ${hoveredBtn === 'disconnect' ? "#ef4444" : "rgba(255, 255, 255, 0.1)"}`, 
      padding: "8px 16px", 
      borderRadius: "8px",
      fontFamily: "inherit", 
      fontSize: "0.9rem",
      fontWeight: "500",
      cursor: "pointer", 
      transition: "all 0.2s ease" 
    },
    fullScreenBtn: { 
      backgroundColor: hoveredBtn === 'fullscreen' ? "rgba(0, 242, 254, 0.15)" : "rgba(15, 23, 42, 0.4)", 
      color: hoveredBtn === 'fullscreen' ? "#00f2fe" : titleColor, 
      border: `1px solid ${hoveredBtn === 'fullscreen' ? "#00f2fe" : "rgba(255, 255, 255, 0.1)"}`, 
      padding: "8px 16px", 
      borderRadius: "8px",
      fontFamily: "inherit", 
      fontSize: "0.9rem",
      fontWeight: "500",
      cursor: "pointer", 
      transition: "all 0.2s ease" 
    },
    chartContainer: {
      ...glassStyle,
      padding: "1.5rem",
      display: "flex",
      flexDirection: "column",
      gap: "1rem"
    },
    chartTitle: {
      fontSize: "0.9rem",
      fontWeight: "500",
      color: subtextColor,
      letterSpacing: "0.5px",
      textTransform: "uppercase"
    }
  };

  return (
    <div style={styles.container}>
      
      {/* --- Left Half: Map --- */}
      <div style={styles.mapSection}>
        <div style={styles.mapWrapper}>
          <CityGridMap cityId={cityId} /> 
        </div>
      </div>

      {/* --- Right Half: Telemetry Dashboard --- */}
      <div style={styles.dashboardSection}>
        
        {/* --- Header Panel --- */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <div style={styles.title}>Telemetry Stream</div>
            <span style={styles.statusDot} title={isConnected ? "WebSocket Connected" : "Disconnected"}></span>
            
            {!isFullScreen && (
              <select 
                style={styles.select} 
                value={cityId} 
                onChange={(e) => {
                  setCityId(e.target.value);
                  navigate(`/dashboard/${e.target.value}`);
                }}
              >
                <option value="aligarh" style={{color: "#000"}}>Aligarh</option>
                <option value="new-delhi" style={{color: "#000"}}>New Delhi</option>
                <option value="bengaluru" style={{color: "#000"}}>Bengaluru</option>
                <option value="mumbai" style={{color: "#000"}}>Mumbai</option>
                <option value="chennai" style={{color: "#000"}}>Chennai</option>
              </select>
            )}
          </div>

          <div style={styles.headerRight}>
            <button 
              style={styles.disconnectBtn}
              onMouseEnter={() => setHoveredBtn('disconnect')}
              onMouseLeave={() => setHoveredBtn(null)}
              onClick={() => navigate('/')} 
            >
              Disconnect
            </button>
            <button 
              style={styles.fullScreenBtn}
              onMouseEnter={() => setHoveredBtn('fullscreen')}
              onMouseLeave={() => setHoveredBtn(null)}
              onClick={() => setIsFullScreen(!isFullScreen)}
            >
              {isFullScreen ? "Restore View" : "Full Screen"}
            </button>
          </div>
        </div>

        {/* --- Data Panels --- */}
        {/* Note: You may need to update the internal styling of MetricsPanel, EnergyChart, and AlertsPanel to match the new theme later */}
        
        <MetricsPanel gridData={gridData} />
        
        <div style={styles.chartContainer}>
           <div style={styles.chartTitle}>Grid Power Consumption (kW)</div>
           <EnergyChart gridData={gridData} gridHistory={gridHistory} />
        </div>

        <AlertsPanel gridData={gridData} />

      </div>
    </div>
  );
}