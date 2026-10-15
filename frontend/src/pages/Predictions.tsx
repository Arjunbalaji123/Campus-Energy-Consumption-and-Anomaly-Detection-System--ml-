import React, { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Prediction } from '../types'
import { BrainCircuit, RefreshCw } from 'lucide-react'

export const Predictions: React.FC = () => {
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchPredictions = async (p = 1) => {
    setLoading(true)
    try {
      const res = await api.getPredictions(p, 20)
      setPredictions(res.items)
      setTotalPages(res.total_pages)
      setTotal(res.total)
      setPage(res.page)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPredictions(1)
  }, [])

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
              Expected Consumption Engine
            </span>
            <span className="text-xs text-slate-400 font-mono">RandomForestRegressor v1.0</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mt-1">Energy Prediction Log</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Model inference history comparing actual campus consumption vs expected baselines.
          </p>
        </div>

        <button
          onClick={() => fetchPredictions(page)}
          className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg font-medium text-sm transition-colors shadow-sm self-start md:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Predictions Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-700">Total Inferences: {total}</span>
          <span className="text-xs text-slate-400">Page {page} of {totalPages || 1}</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-2"></div>
            <p className="text-sm">Loading predictions history...</p>
          </div>
        ) : predictions.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <BrainCircuit className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold text-slate-700">No predictions recorded yet.</p>
            <p className="text-xs text-slate-400 mt-1">Submit an energy reading in Energy Data & Entry to trigger inference.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold uppercase">
                <tr>
                  <th className="px-6 py-3 text-left">Reading ID</th>
                  <th className="px-6 py-3 text-left">Building</th>
                  <th className="px-6 py-3 text-left">Timestamp</th>
                  <th className="px-6 py-3 text-right">Actual kWh</th>
                  <th className="px-6 py-3 text-right">Predicted kWh</th>
                  <th className="px-6 py-3 text-right">Residual</th>
                  <th className="px-6 py-3 text-right">Deviation %</th>
                  <th className="px-6 py-3 text-center">Model Version</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {predictions.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-6 py-3 font-mono font-bold text-slate-900">#{p.reading_id}</td>
                    <td className="px-6 py-3">
                      <span className="font-semibold text-slate-800">{p.building_code}</span>{' '}
                      <span className="text-slate-500">({p.building_name})</span>
                    </td>
                    <td className="px-6 py-3 text-slate-500">
                      {p.timestamp ? new Date(p.timestamp).toLocaleString() : 'N/A'}
                    </td>
                    <td className="px-6 py-3 text-right font-mono font-semibold">
                      {p.actual_energy_kwh != null ? p.actual_energy_kwh.toFixed(1) : 'N/A'}
                    </td>
                    <td className="px-6 py-3 text-right font-mono text-indigo-700 font-semibold">
                      {p.predicted_energy_kwh.toFixed(1)}
                    </td>
                    <td className={`px-6 py-3 text-right font-mono font-semibold ${
                      p.residual_kwh > 5 ? 'text-rose-600' : p.residual_kwh < -5 ? 'text-blue-600' : 'text-slate-600'
                    }`}>
                      {p.residual_kwh > 0 ? `+${p.residual_kwh.toFixed(1)}` : p.residual_kwh.toFixed(1)}
                    </td>
                    <td className="px-6 py-3 text-right font-mono">
                      {p.deviation_pct != null ? `${p.deviation_pct.toFixed(1)}%` : 'N/A'}
                    </td>
                    <td className="px-6 py-3 text-center font-mono text-slate-500">
                      {p.model_version_tag || 'rf_expected_v1'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs">
            <button
              disabled={page <= 1}
              onClick={() => fetchPredictions(page - 1)}
              className="px-3 py-1 bg-white border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-50"
            >
              Previous
            </button>
            <span>Page {page} of {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => fetchPredictions(page + 1)}
              className="px-3 py-1 bg-white border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
