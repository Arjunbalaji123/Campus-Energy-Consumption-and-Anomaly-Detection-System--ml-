import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Building2, Zap, BrainCircuit,
  AlertTriangle, Lightbulb, Activity, Settings as SettingsIcon
} from 'lucide-react'
import { api } from '../services/api'

export default function Navbar() {
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    api.getHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/buildings', label: 'Buildings', icon: Building2 },
    { to: '/energy-data', label: 'Energy Data & Entry', icon: Zap },
    { to: '/predictions', label: 'Predictions', icon: BrainCircuit },
    { to: '/anomalies', label: 'Anomaly Center', icon: AlertTriangle },
    { to: '/recommendations', label: 'Recommendations', icon: Lightbulb },
    { to: '/models', label: 'Model Performance', icon: Activity },
    { to: '/settings', label: 'Settings', icon: SettingsIcon },
  ]

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      {/* Top Banner */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-xs">
            CIT
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 text-base tracking-tight">Campus Energy & Anomaly System</span>
              <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-semibold border border-indigo-200">
                Coimbatore
              </span>
            </div>
            <p className="text-xs text-slate-500">Coimbatore Institute of Technology — Academic Decision Support Prototype</p>
          </div>
        </div>

        {/* Backend Status Indicator */}
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="text-slate-500">Backend API:</span>
          {online === null && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-pulse"></span> Connecting...
            </span>
          )}
          {online === true && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Online
            </span>
          )}
          {online === false && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-semibold">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span> Offline (Port 8000)
            </span>
          )}
        </div>
      </div>

      {/* Navigation Links Bar */}
      <nav className="border-t border-slate-100 bg-slate-50/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex overflow-x-auto space-x-1 py-1.5 scrollbar-none">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md whitespace-nowrap transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`
                }
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </div>
      </nav>
    </header>
  )
}

