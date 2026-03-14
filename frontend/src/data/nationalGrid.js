export const cities = [
  { id: "delhi", name: "Delhi", position: [28.6139, 77.2090] },
  {id: "chennai", name: "Chennai", position: [13.0827, 80.2707] },
  {id:"aligarh", name: "Aligarh", position: [27.8974, 78.0880] },
  { id: "mumbai", name: "Mumbai", position: [19.0760, 72.8777] },
  { id: "bangalore", name: "Bangalore", position: [12.9716, 77.5946] },
  { id: "kolkata", name: "Kolkata", position: [22.5726, 88.3639] },
 
]

export const transmissionLines = [
  { from: "delhi", to: "mumbai" },
  { from: "delhi", to: "kolkata" },
  { from: "mumbai", to: "bangalore" },
  
  { from: "chennai", to: "bangalore" },
  { from: "aligarh", to: "delhi" }
]