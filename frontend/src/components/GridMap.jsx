import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const REGIONAL_DATA = {
  "Uttar Pradesh": ["Aligarh", "Lucknow", "Noida", "Kanpur"],
  "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
  "Karnataka": ["Bengaluru", "Mysuru", "Hubballi"],
  "Delhi": ["New Delhi", "Dwarka"],
  "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"]
};

export default function SystemNavigator() {
  const [time, setTime] = useState(new Date().toLocaleString());
  const [selectedState, setSelectedState] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [isButtonHovered, setIsButtonHovered] = useState(false);
  
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleString()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleStateChange = (e) => {
    setSelectedState(e.target.value);
    setSelectedCity(""); 
  };

  const handleCityChange = (e) => {
    setSelectedCity(e.target.value);
  };

  const initiateUplink = () => {
    if (selectedCity) {
      const formattedCity = selectedCity.toLowerCase().replace(/\s+/g, '-');
      navigate(`/dashboard/${formattedCity}`);
    }
  };

  // --- GLASSMORPHISM & DARK GRADIENT THEME ---
  const textColor = "#e2e8f0"; 
  const titleColor = "#ffffff"; 
  const subtextColor = "#94a3b8"; 

  // Reusable Glass panel style
  const glassStyle = {
    background: "rgba(30, 41, 59, 0.4)", // Semi-transparent dark blue/grey
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)", // For Safari
    border: "1px solid rgba(255, 255, 255, 0.08)",
    boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.3)",
    borderRadius: "16px",
  };

  const styles = {
    wrapper: { 
      // Deep ambient gradient background (Dark Purple to Dark Blue)
      background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #0f172a 100%)",
      color: textColor, 
      fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", 
      padding: "2rem", 
      minHeight: "100vh", 
      display: "flex", 
      flexDirection: "column", 
      boxSizing: "border-box",
      gap: "2rem"
    },
    header: { 
      ...glassStyle,
      display: "flex", 
      justifyContent: "space-between", 
      alignItems: "center", 
      padding: "1.5rem 2rem", 
    },
    title: { 
      fontSize: "1.5rem", 
      fontWeight: "600",
      color: titleColor,
      letterSpacing: "0.5px"
    },
    telemetry: { 
      fontSize: "0.95rem", 
      fontWeight: "500",
      textAlign: "right",
      color: subtextColor
    },
    statusIndicator: {
      display: "inline-block",
      width: "10px",
      height: "10px",
      borderRadius: "50%",
      backgroundColor: "#00f2fe", // Electric blue glow
      marginRight: "8px",
      boxShadow: "0 0 10px #00f2fe, 0 0 20px #00f2fe"
    },
    controlsArea: { 
      ...glassStyle,
      display: "flex", 
      gap: "20px", 
      alignItems: "center", 
      padding: "1.5rem 2rem", 
    },
    label: {
      fontWeight: "500",
      fontSize: "1rem",
      color: titleColor
    },
    selectBox: { 
      backgroundColor: "rgba(15, 23, 42, 0.6)", // Darker translucent background for select
      color: titleColor, 
      border: "1px solid rgba(255, 255, 255, 0.1)", 
      padding: "12px 20px", 
      borderRadius: "12px",
      fontFamily: "inherit",
      fontSize: "1rem",
      outline: "none", 
      cursor: "pointer",
      minWidth: "200px",
      transition: "border-color 0.2s"
    },
    button: { 
      // Vibrant Purple-to-Blue gradient for the call-to-action
      background: "linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)",
      color: "#0f172a", // Dark text for contrast against bright button
      border: "none", 
      padding: "12px 28px", 
      borderRadius: "12px",
      fontFamily: "inherit", 
      fontSize: "1rem",
      fontWeight: "700", 
      cursor: "pointer", 
      boxShadow: isButtonHovered 
        ? "0 0 20px rgba(0, 242, 254, 0.6)" 
        : "0 4px 15px rgba(0, 0, 0, 0.2)",
      transition: "all 0.3s ease",
      marginLeft: "auto",
      transform: isButtonHovered ? "translateY(-2px)" : "translateY(0)"
    },
    viewFrame: { 
      ...glassStyle,
      flexGrow: 1, 
      position: "relative", 
      display: "flex", 
      flexDirection: "column",
      padding: "2rem"
    },
    standbyScreen: { 
      flexGrow: 1, 
      display: "flex", 
      flexDirection: "column", 
      justifyContent: "center", 
      alignItems: "center", 
      textAlign: "center" 
    },
    screenTitle: {
      fontSize: "2.5rem",
      fontWeight: "300",
      color: titleColor,
      marginBottom: "1rem",
      background: "linear-gradient(90deg, #e2e8f0 0%, #94a3b8 100%)",
      WebkitBackgroundClip: "text",
      WebkitTextFillColor: "transparent"
    },
    screenSubtitle: {
      fontSize: "1.1rem",
      color: subtextColor
    },
    footer: { 
      padding: "0.5rem 1rem", 
      fontSize: "0.85rem", 
      display: "flex", 
      justifyContent: "space-between",
      color: subtextColor,
      fontWeight: "500"
    }
  };

  return (
    <div style={styles.wrapper}>
      {/* --- Top Control Panel --- */}
      <div style={styles.header}>
        <div style={styles.title}>Regional Grid Management Portal</div>
        <div style={styles.telemetry}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", marginBottom: "4px" }}>
            <span style={styles.statusIndicator}></span>
            <span style={{ color: titleColor, fontWeight: "600" }}>System Online</span>
          </div>
          <div>{time}</div>
        </div>
      </div>

      {/* --- Routing Parameters --- */}
      <div style={styles.controlsArea}>
        <span style={styles.label}>Target Region:</span>
        
        <select 
          style={styles.selectBox} 
          value={selectedState} 
          onChange={handleStateChange}
        >
          <option value="" style={{ color: "#000" }}>Select State...</option>
          {Object.keys(REGIONAL_DATA).map(state => (
            <option key={state} value={state} style={{ color: "#000" }}>{state}</option>
          ))}
        </select>
        
        <select 
          style={styles.selectBox} 
          value={selectedCity} 
          onChange={handleCityChange} 
          disabled={!selectedState}
        >
          <option value="" style={{ color: "#000" }}>Select City...</option>
          {selectedState && REGIONAL_DATA[selectedState].map(city => (
            <option key={city} value={city} style={{ color: "#000" }}>{city}</option>
          ))}
        </select>

        {selectedCity && (
          <button 
            style={styles.button} 
            onClick={initiateUplink}
            onMouseEnter={() => setIsButtonHovered(true)}
            onMouseLeave={() => setIsButtonHovered(false)}
          >
            Connect to Dashboard
          </button>
        )}
      </div>

      {/* --- Main Embedded Display --- */}
      <div style={styles.viewFrame}>
        <div style={styles.standbyScreen}>
          <h2 style={styles.screenTitle}>System Standby</h2>
          {selectedCity ? (
            <p style={{ ...styles.screenSubtitle, color: "#00f2fe", fontWeight: "500" }}>
              Region locked to {selectedCity}. Ready to initialize monitoring.
            </p>
          ) : (
            <p style={styles.screenSubtitle}>
              Please select a geographic parameter above to view grid telemetry.
            </p>
          )}
        </div>
      </div>

      {/* --- Footer Status --- */}
      <div style={styles.footer}>
        <span>{selectedCity ? `Target: ${selectedCity}, ${selectedState}` : "Status: Awaiting Configuration"}</span>
        <span>Secure Session</span>
      </div>
    </div>
  );
}