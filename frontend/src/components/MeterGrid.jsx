import { useEffect, useState } from "react"
import { fetchMeterData } from "../services/api"
import EnergyChart from "../charts/EnergyChart"

export default function MeterGrid({ meterId }) {

  const [data, setData] = useState(null)

  useEffect(() => {

    fetchMeterData(meterId).then(res => {
      setData(res.series)
    })

  }, [meterId])

  if (!data) return <p>Loading meter data...</p>

  return (

    <div>
      <h2>Meter {meterId}</h2>
      <EnergyChart data={data} />
    </div>

  )
}