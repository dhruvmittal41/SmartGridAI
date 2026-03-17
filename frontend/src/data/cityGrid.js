import gridDatabase from './gridData.json';

export function getCityGrid(cityId) {
  const cityData = gridDatabase[cityId];


  if (!cityData) {
    console.warn(`City ID "${cityId}" not found in database.`);
    return { center: [28.6139, 77.2090], substations: [], transformers: [], meters: [] };
  }

  const substations = [];
  const transformers = [];
  const meters = [];


  cityData.substations.forEach((sub) => {
    substations.push({
      id: sub.id,
      type: "substation",
      label: sub.label,
      lat: sub.lat,
      lng: sub.lng
    });

    if (sub.transformers) {
      sub.transformers.forEach((tr) => {
        transformers.push({
          id: tr.id,
          type: "transformer",
          parent: sub.id, 
          label: tr.label,
          lat: tr.lat,
          lng: tr.lng
        });

        if (tr.meters) {
          tr.meters.forEach((m) => {
            meters.push({
              id: m.id,
              type: "meter",
              parent: tr.id, 
              label: m.label,
              lat: m.lat,
              lng: m.lng
            });
          });
        }
      });
    }
  });

  return {
    center: cityData.center, 
    substations,
    transformers,
    meters
  };
}