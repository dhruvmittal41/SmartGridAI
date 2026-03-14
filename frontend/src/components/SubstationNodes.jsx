import { Marker, Tooltip } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import { cities } from "../data/nationalGrid";
import L from 'leaflet';

const pulsingStyle = `
  @keyframes pulse-ring {
    0% { transform: scale(0.33); opacity: 0.8; }
    80%, 100% { transform: scale(1); opacity: 0; }
  }
  
  /* 1. Target the root Leaflet div to clear defaults without breaking positioning */
  .clear-leaflet-icon {
    background: transparent !important;
    border: none !important;
  }

  /* 2. Our safe, isolated internal wrapper */
  .sensor-node {
    position: relative; 
    width: 30px;
    height: 30px;
    cursor: pointer;
  }

  .pulse {
    position: absolute;
    top: 0;
    left: 0;
    width: 30px;
    height: 30px;
    box-sizing: border-box;
    border: 2px solid #00ff41;
    border-radius: 50%;
    animation: pulse-ring 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
  }
  
  .dot {
    position: absolute;
    top: 11px; 
    left: 11px;
    width: 8px;
    height: 8px;
    background: #00ff41;
    border-radius: 50%;
    box-shadow: 0 0 10px #00ff41;
    transition: all 0.2s ease-in-out;
  }
  
  .sensor-node:hover .dot {
    background: #ffffff;
    box-shadow: 0 0 15px #ffffff;
  }
`;

// Wrap our HTML in the new .sensor-node div
const createCyberIcon = () => L.divIcon({
  className: 'clear-leaflet-icon',
  html: `<div class="sensor-node">
           <div class="pulse"></div>
           <div class="dot"></div>
         </div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15] 
});

export default function SubstationNodes() {
  const navigate = useNavigate();

  return (
    <>
      <style>{pulsingStyle}</style>
      {cities.map((city) => (
        <Marker 
          key={city.id} 
          position={city.position} 
          icon={createCyberIcon()}
          eventHandlers={{
            click: () => {
              navigate(`/city/${city.id}`);
            },
          }}
        >
          <Tooltip direction="top" offset={[0, -10]} opacity={1} sticky>
            <div style={{
              backgroundColor: "#050505",
              color: "#00ff41",
              border: "1px solid #00ff41",
              fontFamily: "'Courier New', monospace",
              fontSize: "10px",
              padding: "2px 6px",
              textTransform: "uppercase"
            }}>
              NODE_{city.id.toUpperCase()} // LVL_OK
            </div>
          </Tooltip>
        </Marker>
      ))}
    </>
  );
}