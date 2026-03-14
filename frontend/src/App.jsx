import { BrowserRouter, Routes, Route } from "react-router-dom"
import NationalGrid from "./pages/NationalGrid"

import MeterView from "./pages/MeterView"
import DashboardLayout from "./pages/DashboardLayout"

export default function App() {

  return (

    <BrowserRouter>

      <Routes>

        <Route path="/" element={<NationalGrid />} />

        <Route path="/city/:cityId" element={<DashboardLayout />} />

        <Route path="/meter/:meterId" element={<MeterView />} />

      </Routes>

    </BrowserRouter>

  )
}