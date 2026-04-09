export const substations = [
  { id: 1, name: "Delhi", position: [28.6139, 77.2090] },
  { id: 2, name: "Mumbai", position: [19.0760, 72.8777] },
  { id: 3, name: "Bangalore", position: [12.9716, 77.5946] },
  { id: 4, name: "Chennai", position: [13.0827, 80.2707] },
  { id: 5, name: "Kolkata", position: [22.5726, 88.3639] }
]

export const transmissionLines = [
  { from: "Delhi", to: "Mumbai", status: "normal" },
  { from: "Mumbai", to: "Bangalore", status: "normal" },
  { from: "Bangalore", to: "Chennai", status: "normal" },
  { from: "Delhi", to: "Kolkata", status: "normal" }
]