import { generateMeterSeries } from "../data/meterData"

export function fetchMeterData(meterId) {

  return new Promise((resolve) => {

    setTimeout(() => {

      resolve({
        meterId,
        series: generateMeterSeries()
      })

    }, 500)

  })
}