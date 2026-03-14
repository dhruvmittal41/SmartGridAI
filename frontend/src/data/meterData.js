export function generateMeterSeries() {

  const data = []

  for (let i = 0; i < 24; i++) {

    data.push({
      time: `${i}:00`,
      energy: +(Math.random() * 2 + 0.5).toFixed(2),
      voltage: +(220 + Math.random() * 20).toFixed(1),
      current: +(3 + Math.random() * 5).toFixed(1)
    })
  }

  return data
}