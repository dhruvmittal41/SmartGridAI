import { writeFileSync } from 'fs';


const cities = {
  aligarh: { name: "Aligarh", prefix: "ALI", center: [27.8974, 78.0880] },
  delhi: { name: "New Delhi", prefix: "DEL", center: [28.6139, 77.2090] },
  bangalore: { name: "Bangalore", prefix: "BLR", center: [12.9716, 77.5946] },
  mumbai: { name: "Mumbai", prefix: "MUM", center: [19.0760, 72.8777] },
  chennai: { name: "Chennai", prefix: "CHE", center: [13.0827, 80.2707] }
};


const applyOffset = (coord, maxOffset) => coord + (Math.random() - 0.5) * maxOffset;

const database = {};

for (const [cityKey, cityInfo] of Object.entries(cities)) {
  database[cityKey] = {
    name: cityInfo.name,
    center: cityInfo.center,
    substations: []
  };


  for (let s = 1; s <= 3; s++) {
    const subLat = applyOffset(cityInfo.center[0], 0.08);
    const subLng = applyOffset(cityInfo.center[1], 0.08);
    const subId = `${cityInfo.prefix}-S${s}`;

    const substation = {
      id: subId,
      label: `${cityInfo.name} Substation ${s}`,
      lat: parseFloat(subLat.toFixed(5)),
      lng: parseFloat(subLng.toFixed(5)),
      transformers: []
    };

 
    for (let t = 1; t <= 4; t++) {
      const transLat = applyOffset(subLat, 0.02);
      const transLng = applyOffset(subLng, 0.02);
      const transId = `${subId}-T${t}`;

      const transformer = {
        id: transId,
        label: `Trafo ${t}`,
        lat: parseFloat(transLat.toFixed(5)),
        lng: parseFloat(transLng.toFixed(5)),
        meters: []
      };

   
      for (let m = 1; m <= 10; m++) {
        const meterLat = applyOffset(transLat, 0.004);
        const meterLng = applyOffset(transLng, 0.004);
        
        transformer.meters.push({
          id: `${transId}-M${m}`,
          label: `Meter ${m}`,
          lat: parseFloat(meterLat.toFixed(5)),
          lng: parseFloat(meterLng.toFixed(5))
        });
      }
      substation.transformers.push(transformer);
    }
    database[cityKey].substations.push(substation);
  }
}


writeFileSync('gridData.json', JSON.stringify(database, null, 2));
console.log("✅ Successfully generated gridData.json with 5 cities, 15 substations, 60 transformers, and 600 meters!");