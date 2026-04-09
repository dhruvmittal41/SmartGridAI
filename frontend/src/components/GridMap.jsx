import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Swal from "sweetalert2";
import { useGridStream } from "../hooks/useGridStream"; // Added hook import

const REGIONAL_DATA = {
  "Uttar Pradesh": ["Aligarh", "Lucknow", "Noida", "Kanpur"],
  "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
  "Karnataka": ["Bengaluru", "Mysuru", "Hubballi"],
  "Delhi": ["New Delhi", "Dwarka"],
  "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"]
};

const SUBSTATIONS = [
  {
    id: "substation1",
    name: "Substation 1",
    color: "linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)",
    glow: "rgba(255, 75, 43, 0.6)", 
    icon: "⚡"
  },
  {
    id: "substation2",
    name: "Substation 2",
    color: "linear-gradient(135deg, #00c6ff 0%, #0072ff 100%)",
    glow: "rgba(0, 198, 255, 0.6)",
    icon: "⚡"
  },
  {
    id: "substation3",
    name: "Substation 3",
    color: "linear-gradient(135deg, #00f260 0%, #0575e6 100%)",
    glow: "rgba(0, 242, 96, 0.6)",
    icon: "⚡"
  }
];

export default function SystemNavigator() {
  const [time, setTime] = useState(new Date().toLocaleString());
  const [selectedState, setSelectedState] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [faultyStation, setFaultyStation] = useState(null);

  const navigate = useNavigate();
  
  const { gridData, isConnected } = useGridStream();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleString()), 1000);
    return () => clearInterval(timer);
  }, []);


  useEffect(() => {
    if (!isConnected || !gridData || faultyStation) return;

    
    const faultProbability = 0.08; 

    if (Math.random() < faultProbability) {
      const randomIndex = 0
      const targetStation = SUBSTATIONS[randomIndex].id;

      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFaultyStation(targetStation);

      setTimeout(() => {
        setFaultyStation(null);
      }, 12000); 
    }
  }, [gridData, isConnected, faultyStation]); 
  const handleStateChange = (e) => {
    setSelectedState(e.target.value);
    setSelectedCity("");
  };

  const handleCityChange = (e) => {
    setSelectedCity(e.target.value);
  };

  const openSubstationDashboard = (station) => {
    const formattedCity = selectedCity.toLowerCase().replace(/\s+/g, "-");

    Swal.fire({
      title: 'Initialize Uplink?',
      text: `Establish connection to ${station.name} in ${selectedCity}?`,
      icon: 'info',
      showCancelButton: true,
      confirmButtonColor: '#00f2fe',
      cancelButtonColor: '#334155',
      confirmButtonText: 'Yes, Connect',
      cancelButtonText: 'Cancel',
      background: '#0f172a',
      color: '#e2e8f0',
      backdrop: 'rgba(0,0,0,0.6)',
    }).then((result) => {
      if (result.isConfirmed) {
        navigate(`/dashboard/${formattedCity}`);
      }
    });
  };

  const styles = {
   wrapper: {
      background: "radial-gradient(circle at top, #1e1e38, #0f172a, #020617)",
      color: "#e2e8f0",
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
      padding: "2rem",
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      gap: "1.5rem",
      boxSizing: "border-box"
     },
    baseGlass: {
      backdropFilter: "blur(16px)",
      WebkitBackdropFilter: "blur(16px)",
      borderRadius: "20px",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)"
    },

    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "1.2rem 2rem",
      background: "rgba(88, 28, 135, 0.35)", 
      border: "1px solid rgba(168, 85, 247, 0.4)",
    },

    title: {
      fontSize: "1.75rem",
      fontWeight: "700",
      background: "linear-gradient(to right, #fff, #d8b4fe)",
      WebkitBackgroundClip: "text",
      WebkitTextFillColor: "transparent",
      letterSpacing: "0.5px"
    },

    telemetry: {
      textAlign: "right",
      fontSize: "0.95rem",
      color: "#d8b4fe",
      display: "flex",
      flexDirection: "column",
      gap: "4px"
    },

    statusIndicator: {
      width: "12px",
      height: "12px",
      borderRadius: "50%",
      background: isConnected ? "#00f2fe" : "#ef4444", // Synced to stream
      boxShadow: isConnected ? "0 0 12px #00f2fe, 0 0 24px #00f2fe" : "0 0 12px #ef4444",
      transition: "all 0.3s ease"
    },

    controlsArea: {
      display: "flex",
      gap: "20px",
      alignItems: "center",
      padding: "1.5rem 2rem",
      background: "rgba(15, 118, 110, 0.35)", 
      border: "1px solid rgba(45, 212, 191, 0.4)",
    },

    selectBox: {
      background: "rgba(2, 44, 34, 0.8)", 
      color: "#ccfbf1",
      border: "1px solid rgba(45, 212, 191, 0.3)",
      padding: "14px 20px",
      borderRadius: "12px",
      fontSize: "1rem",
      minWidth: "220px",
      outline: "none",
      cursor: "pointer",
      transition: "border-color 0.3s ease",
      appearance: "none"
    },

    viewFrame: {
      flexGrow: 1,
      padding: "2rem",
      display: "flex",
      flexDirection: "column",
      background: "rgba(30, 58, 138, 0.25)", 
      border: "1px solid rgba(96, 165, 250, 0.4)",
    },

    standbyScreen: {
      flexGrow: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center"
    },

    screenTitle: {
      fontSize: "2.2rem",
      fontWeight: "400",
      marginBottom: "0.5rem",
      color: "#bfdbfe"
    },

    screenSubtitle: {
      color: "#93c5fd",
      fontSize: "1.1rem"
    },

    substationGrid: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
      gap: "2.5rem",
      marginTop: "1.5rem",
      flexGrow: 1 
    },

    substationCard: {
      borderRadius: "24px",
      padding: "2rem",
      color: "#fff",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      cursor: "pointer",
      position: "relative",
      transition: "all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
      border: "1px solid rgba(255,255,255,0.2)",
    },

    cardIcon: {
      fontSize: "3.5rem",
      marginBottom: "1rem",
      filter: "drop-shadow(0px 4px 8px rgba(0,0,0,0.4))"
    },

    cardName: {
      fontSize: "1.6rem",
      fontWeight: "700",
      letterSpacing: "1px",
      textShadow: "0 2px 4px rgba(0,0,0,0.5)"
    },
    statusBadge: {
      marginTop: "1.2rem",
      padding: "6px 14px",
      borderRadius: "20px",
      fontSize: "0.85rem",
      fontWeight: "600",
      letterSpacing: "1px",
      backgroundColor: "rgba(0,0,0,0.3)",
      border: "1px solid rgba(255,255,255,0.2)",
      display: "flex",
      alignItems: "center",
      gap: "8px",
      boxShadow: "inset 0 0 10px rgba(0,0,0,0.5)"
    },
    footer: {
      fontSize: "0.85rem",
      display: "flex",
      justifyContent: "space-between",
      color: "#64748b",
      padding: "0 1rem"
    }
  };

  return (
    <div style={styles.wrapper}>

      <div style={{ ...styles.baseGlass, ...styles.header }}>
        <div style={styles.title}>Regional Grid Management</div>

        <div style={styles.telemetry}>
          <div style={{ display: "flex", gap: "10px", alignItems: "center", justifyContent: "flex-end" }}>
            <span style={styles.statusIndicator}></span>
            <span style={{ color: "#f8fafc", fontWeight: "600", letterSpacing: "0.5px" }}>
              {isConnected ? "SYS.ONLINE" : "SYS.OFFLINE"}
            </span>
          </div>
          <div style={{ fontFamily: "monospace", marginTop: "4px" }}>{time}</div>
        </div>
       </div>
      
      <div style={{ ...styles.baseGlass, ...styles.controlsArea }}>
        <select
          style={styles.selectBox}
          value={selectedState}
          onChange={handleStateChange}
          onFocus={(e) => (e.target.style.borderColor = "#2dd4bf")}
          onBlur={(e) => (e.target.style.borderColor = "rgba(45, 212, 191, 0.3)")}
        >
          <option value="" disabled>Select State Region</option>
          {Object.keys(REGIONAL_DATA).map((state) => (
            <option key={state} value={state}>{state}</option>
          ))}
        </select>

        <select
          style={styles.selectBox}
          value={selectedCity}
          onChange={handleCityChange}
          disabled={!selectedState}
          onFocus={(e) => (e.target.style.borderColor = "#2dd4bf")}
          onBlur={(e) => (e.target.style.borderColor = "rgba(45, 212, 191, 0.3)")}
        >
          <option value="" disabled>Select Target City</option>
          {selectedState &&
            REGIONAL_DATA[selectedState].map((city) => (
              <option key={city} value={city}>{city}</option>
            ))}
        </select>
      </div>

 
      <div style={{ ...styles.baseGlass, ...styles.viewFrame }}>
        {!selectedCity ? (
          <div style={styles.standbyScreen}>
            <div style={{ fontSize: "4rem", marginBottom: "1rem", opacity: 0.5 }}>📡</div>
            <h2 style={styles.screenTitle}>System Standby</h2>
            <p style={styles.screenSubtitle}>
              Please select a state and city to configure regional substations.
            </p>
          </div>
        ) : (
          <>
            <h2 style={{ ...styles.screenTitle, fontSize: "1.8rem" }}>Available Nodes</h2>
            <p style={styles.screenSubtitle}>Select a substation to initialize local dashboard.</p>

            <div style={styles.substationGrid}>
              {SUBSTATIONS.map((station) => {
                const isFaulty = station.id === faultyStation;
                const statusText = isFaulty ? "FAULT" : "NORMAL";
                const dotColor = isFaulty ? "#ff4444" : "#4ade80";

                return (
                  <div
                    key={station.id}
                    style={{
                      ...styles.substationCard,
                      background: station.color,
                      boxShadow: `0 0 25px ${station.glow}, inset 0 0 15px rgba(255,255,255,0.2)`
                    }}
                    onClick={() => openSubstationDashboard(station)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-15px) scale(1.03)";
                      e.currentTarget.style.boxShadow = `0 0 50px ${station.glow}, inset 0 0 25px rgba(255,255,255,0.4)`;
                      e.currentTarget.style.borderColor = "#fff";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "translateY(0) scale(1)";
                      e.currentTarget.style.boxShadow = `0 0 25px ${station.glow}, inset 0 0 15px rgba(255,255,255,0.2)`;
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.2)";
                    }}
                  >
                    <div style={styles.cardIcon}>{station.icon}</div>
                    <div style={styles.cardName}>{station.name}</div>
                    
                    <div style={styles.statusBadge}>
                      <span style={{
                        width: "10px", 
                        height: "10px", 
                        borderRadius: "50%",
                        backgroundColor: dotColor,
                        boxShadow: `0 0 8px ${dotColor}`
                      }}></span>
                      STATUS: {statusText}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      <div style={styles.footer}>
        <span>
          {selectedCity
            ? `TARGET LOCK: ${selectedCity.toUpperCase()} // ${selectedState.toUpperCase()}`
            : "AWAITING CONFIGURATION"}
        </span>
        <span style={{ display: "flex", gap: "15px" }}>
          <span>NODE: v2.4.2</span>
          <span>SECURE SESSION ENCRYPTED</span>
        </span>
      </div>
    </div>
  );
}