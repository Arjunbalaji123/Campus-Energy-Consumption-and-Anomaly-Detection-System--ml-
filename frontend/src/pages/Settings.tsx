import React, { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Sliders, Check } from 'lucide-react'

export const Settings: React.FC = () => {
  const [warningThreshold, setWarningThreshold] = useState<number>(20)
  const [criticalThreshold, setCriticalThreshold] = useState<number>(40)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSettings()
      .then((data) => {
        if (data.thresholds) {
          setWarningThreshold(data.thresholds.warning_percentage || 20)
          setCriticalThreshold(data.thresholds.critical_percentage || 40)
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.updateThresholds(warningThreshold, criticalThreshold)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      alert('Failed to update system thresholds.')
    }
  }

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-2"></div>
        <p className="text-sm">Loading system settings...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
            System Calibration
          </span>
          <span className="text-xs text-slate-400 font-mono">Academic Parameters</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-800 mt-1">System Configuration & Thresholds</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Tune residual threshold percentages, data sources, and building energy baseline parameters.
        </p>
      </div>

      {saved && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center gap-2">
          <Check className="w-5 h-5 text-emerald-600" />
          <span>Threshold configuration updated and persisted.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-indigo-600" />
            Residual-Based Anomaly Detection Thresholds
          </h2>
          <p className="text-xs text-slate-500">
            Deviations between actual meter readings and Random Forest predictions are evaluated against these percentages.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-700">
              Warning Severity Threshold (%)
            </label>
            <input
              type="number"
              min="5"
              max="100"
              value={warningThreshold}
              onChange={(e) => setWarningThreshold(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-400">
              Readings exceeding predicted expected consumption by this percentage trigger a Warning alert.
            </p>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-700">
              Critical Severity Threshold (%)
            </label>
            <input
              type="number"
              min="10"
              max="200"
              value={criticalThreshold}
              onChange={(e) => setCriticalThreshold(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-400">
              Readings exceeding predicted expected consumption by this percentage trigger a Critical alert.
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100 flex justify-end">
          <button
            type="submit"
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            Save Configuration
          </button>
        </div>
      </form>
    </div>
  )
}
