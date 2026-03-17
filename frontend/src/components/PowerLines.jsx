import React, { useState, useEffect, Fragment } from "react";
import { Polyline } from "react-leaflet";
import { cities, transmissionLines } from "../data/nationalGrid";

const FlowingLine = ({ positions, color = "cyan" }) => {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    let animationFrame;
    const animate = () => {
      setOffset((prev) => (prev - 1) % 20); 
      animationFrame = requestAnimationFrame(animate);
    };
    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, []);

  return (
    <Polyline
      positions={positions}
      pathOptions={{
        color: color,
        weight: 4,
        dashArray: "10, 10", 
        dashOffset: offset.toString(),
        lineCap: "round",
        opacity: 0.8
      }}
    />
  );
};

export default function PowerLines() {
  const getCoords = (id) => cities.find((c) => c.id === id).position;

  return (
    <>
      {transmissionLines.map((line, i) => {
        const coords = [getCoords(line.from), getCoords(line.to)];
        
        return (
       
          <Fragment key={i}>
          
            <Polyline 
              positions={coords} 
              pathOptions={{ color: "green", weight: 6, opacity: 0.2 }} 
            />
            
            <FlowingLine 
              positions={coords} 
              color={line.load > 80 ? "red" : "#00ffff"} 
            />
          </Fragment>
        );
      })}
    </>
  );
}