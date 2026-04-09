import { BrowserRouter, Routes, Route } from "react-router-dom"
import NationalGrid from "./pages/NationalGrid"

import MeterView from "./pages/MeterView"
import DashboardLayout from "./pages/DashboardLayout"
import Landing from "./pages/Landing"

export default function App() {

  return (

    <BrowserRouter>

      <Routes>
        <Route path="/" element={<Landing/>} />
        <Route path="/national" element={<NationalGrid />} />

        <Route path="/dashboard/:cityId" element={<DashboardLayout />} />

        <Route path="/meter/:meterId" element={<MeterView />} />

      </Routes>

    </BrowserRouter>

  )
}