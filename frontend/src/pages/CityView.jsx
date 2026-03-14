import { useParams } from "react-router-dom"
import CityGrid from "../components/CityGrid"

export default function CityView() {

  const { cityId } = useParams()

  return (
    <div>
      <h1>{cityId} Grid</h1>
      <CityGrid cityId={cityId} />
    </div>
  )

}