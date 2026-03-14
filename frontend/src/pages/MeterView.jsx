import { useParams } from "react-router-dom"
import MeterGrid from "../components/MeterGrid"

export default function MeterView() {

  const { meterId } = useParams()

  return (

    <div>
      <MeterGrid meterId={meterId} />
    </div>

  )
}