import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import { Overview } from './pages/Overview'
import { Buildings } from './pages/Buildings'
import EnergyData from './pages/EnergyData'
import { Predictions } from './pages/Predictions'
import { AnomalyCenter } from './pages/AnomalyCenter'
import { Recommendations } from './pages/Recommendations'
import { Sustainability } from './pages/Sustainability'
import { ModelPerformance } from './pages/ModelPerformance'
import { Settings } from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
        {/* Navigation Header */}
        <Navbar />

        {/* Dynamic Route Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/buildings" element={<Buildings />} />
            <Route path="/energy-data" element={<EnergyData />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/anomalies" element={<AnomalyCenter />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/sustainability" element={<Sustainability />} />
            <Route path="/models" element={<ModelPerformance />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        {/* Academic Prototype Footer */}
        <footer className="bg-white border-t border-slate-200 mt-auto py-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
            <div>
              <p className="font-semibold text-slate-700">
                AI-Based Campus Energy Consumption & Anomaly Detection System
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Academic Research Prototype • Coimbatore Institute of Technology (CIT), Coimbatore
              </p>
            </div>
            <div className="flex items-center gap-4 text-[11px]">
              <span className="inline-flex items-center gap-1.5 text-slate-500">
                <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                FastAPI + PyTorch/Scikit-Learn + React
              </span>
              <span>•</span>
              <span className="text-slate-400">Coimbatore Climate Context (SW/NE Monsoon)</span>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  )
}
