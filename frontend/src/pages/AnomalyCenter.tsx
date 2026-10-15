import React, { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { AnomalyEvent } from '../types'
import {
  CheckCircle, ShieldAlert, FileText, Search,
  RefreshCw, User, ChevronRight, X, Sparkles
} from 'lucide-react'

export const AnomalyCenter: React.FC = () => {
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [methodFilter, setMethodFilter] = useState<string>('')

  // Batch scan state
  const [scanning, setScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState<string | null>(null)

  // Selected Anomaly for Deep Forensic Investigation Dossier Modal
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyEvent | null>(null)

  const fetchAnomalies = async (p = 1) => {
    setLoading(true)
    try {
      const res = await api.getAnomalies(
        p,
        15,
        severityFilter || undefined,
        statusFilter || undefined
      )
      setAnomalies(res.items)
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
    fetchAnomalies(1)
  }, [severityFilter, statusFilter, methodFilter])

  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      const updated = await api.updateAnomalyStatus(id, newStatus)
      setAnomalies((prev) => prev.map((a) => (a.id === id ? { ...a, status: updated.status } : a)))
      if (selectedAnomaly && selectedAnomaly.id === id) {
        setSelectedAnomaly({ ...selectedAnomaly, status: updated.status })
      }
    } catch (err) {
      alert('Failed to update anomaly status.')
    }
  }

  const handleRecommendationStatusChange = async (recId: number, newStatus: string) => {
    try {
      await api.updateRecommendationStatus(recId, newStatus)
      if (selectedAnomaly && selectedAnomaly.recommendations) {
        const updatedRecs = selectedAnomaly.recommendations.map((r) =>
          r.id === recId ? { ...r, status: newStatus as any } : r
        )
        setSelectedAnomaly({ ...selectedAnomaly, recommendations: updatedRecs })
      }
    } catch (err) {
      alert('Failed to update recommendation status.')
    }
  }

  const handleRunBatchScan = async () => {
    setScanning(true)
    setScanMessage(null)
    try {
      const res = await api.runBatchScan(2000)
      setScanMessage(res.message)
      fetchAnomalies(1)
      setTimeout(() => setScanMessage(null), 6000)
    } catch (err: any) {
      alert(err.message || 'Batch scan failed.')
    } finally {
      setScanning(false)
    }
  }

  // Filtered by method on client side if needed
  const filteredAnomalies = anomalies.filter((a) => {
    if (!methodFilter) return true
    return a.detection_method === methodFilter
  })

  // Summary counts
  const criticalCount = anomalies.filter((a) => a.severity === 'critical').length
  const dualCount = anomalies.filter((a) => a.detection_method === 'dual').length
  const openCount = anomalies.filter((a) => a.status === 'open' || a.status === 'investigating').length

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
              <ShieldAlert className="w-3.5 h-3.5" />
              Surveillance & Forensics
            </span>
            <span className="text-xs text-slate-400 font-mono">Phase 11 Investigation Workspace</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mt-1">Campus Anomaly Center</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Forensic root-cause explanation engine, physical hypothesis verification, and operational decision support.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunBatchScan}
            disabled={scanning}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm transition-colors shadow-sm disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            {scanning ? 'Scanning Observations...' : 'Run Surveillance Batch Scan'}
          </button>
          <button
            onClick={() => fetchAnomalies(page)}
            className="p-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-sm transition-colors"
            title="Refresh anomalies"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Batch Scan Feedback Alert */}
      {scanMessage && (
        <div className="p-4 bg-indigo-50 border border-indigo-200 text-indigo-900 rounded-xl text-xs flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-indigo-600 shrink-0" />
            <span className="font-medium">{scanMessage}</span>
          </div>
          <button onClick={() => setScanMessage(null)} className="font-bold text-indigo-600">✕</button>
        </div>
      )}

      {/* KPI Stats Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Flagged</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{total}</div>
          <span className="text-xs text-slate-400">Total detected campus anomalies</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Critical Severity</span>
          <div className="text-2xl font-bold text-rose-600 mt-1">{criticalCount}</div>
          <span className="text-xs text-slate-400">Exceeds +40% residual threshold</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Dual-Method Confirmed</span>
          <div className="text-2xl font-bold text-indigo-600 mt-1">{dualCount}</div>
          <span className="text-xs text-slate-400">Residual & Isolation Forest agreement</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active Investigations</span>
          <div className="text-2xl font-bold text-amber-600 mt-1">{openCount}</div>
          <span className="text-xs text-slate-400">Open or under review</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
            <Search className="w-4 h-4 text-indigo-600" />
            <span>Filters:</span>
          </div>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical (&gt; +40%)</option>
            <option value="warning">Warning (+20% to +40%)</option>
            <option value="normal">Normal</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
          >
            <option value="">All Lifecycle Statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>

          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
          >
            <option value="">All Detection Methods</option>
            <option value="dual">Dual-Method Confirmed</option>
            <option value="residual">Residual Analysis</option>
            <option value="isolation_forest">Isolation Forest</option>
          </select>
        </div>

        <span className="text-xs text-slate-500">
          Showing {filteredAnomalies.length} of {total} anomaly events
        </span>
      </div>

      {/* Anomalies List */}
      {loading ? (
        <div className="p-12 text-center text-slate-500">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-2"></div>
          <p className="text-sm">Loading campus anomaly events...</p>
        </div>
      ) : filteredAnomalies.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-2">
          <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto" />
          <p className="font-semibold text-slate-800 text-base">No anomalies matching filters</p>
          <p className="text-xs text-slate-400">All campus facilities are operating within normal baseline limits.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredAnomalies.map((anom) => {
            const hasExplanations = anom.explanations && anom.explanations.length > 0
            const firstExpl = hasExplanations ? anom.explanations![0] : null

            return (
              <div
                key={anom.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-indigo-300 transition-colors"
              >
                {/* Event Card Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-1 text-xs font-bold uppercase rounded-md ${
                        anom.severity === 'critical'
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : 'bg-amber-100 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {anom.severity}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-900 text-sm">
                          {anom.building_code}
                        </span>
                        <span className="text-slate-600 text-sm">{anom.building_name}</span>
                        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                          Method: {anom.detection_method}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Observation: {new Date(anom.timestamp).toLocaleString()} • Event ID #{anom.id}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <select
                      value={anom.status}
                      onChange={(e) => handleStatusChange(anom.id, e.target.value)}
                      className={`px-2.5 py-1 text-xs border rounded-lg font-semibold focus:outline-none ${
                        anom.status === 'resolved'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : anom.status === 'investigating'
                          ? 'bg-amber-50 text-amber-800 border-amber-200'
                          : 'bg-slate-50 text-slate-700 border-slate-200'
                      }`}
                    >
                      <option value="open">Status: Open</option>
                      <option value="investigating">Status: Investigating</option>
                      <option value="resolved">Status: Resolved</option>
                      <option value="dismissed">Status: Dismissed</option>
                    </select>

                    <button
                      onClick={() => setSelectedAnomaly(anom)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded-lg text-xs transition-colors"
                    >
                      <span>Investigate Dossier</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Forensic Metric Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg text-xs">
                  <div>
                    <span className="text-slate-400 block">Observed Energy:</span>
                    <span className="font-bold text-slate-800 text-sm">{anom.actual_energy_kwh.toFixed(1)} kWh</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Expected Baseline:</span>
                    <span className="font-bold text-slate-800 text-sm">
                      {anom.predicted_energy_kwh != null ? `${anom.predicted_energy_kwh.toFixed(1)} kWh` : 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Residual Deviation:</span>
                    <span className={`font-bold text-sm ${anom.residual_kwh && anom.residual_kwh > 0 ? 'text-rose-600' : 'text-slate-800'}`}>
                      {anom.residual_kwh != null ? `+${anom.residual_kwh.toFixed(1)} kWh` : 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Percentage Deviation:</span>
                    <span className="font-bold text-rose-600 text-sm">
                      {anom.deviation_pct != null ? `+${anom.deviation_pct.toFixed(1)}%` : 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Primary Physical Hypothesis Callout */}
                {firstExpl && (
                  <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-amber-900 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-amber-700" />
                        Forensic Explanation: {firstExpl.primary_hypothesis}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900 uppercase">
                        Confidence: {firstExpl.confidence}
                      </span>
                    </div>
                    {firstExpl.recommended_next_action && (
                      <p className="text-slate-600">
                        <strong className="text-slate-800">Action:</strong> {firstExpl.recommended_next_action}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="p-4 bg-white rounded-xl border border-slate-200 flex items-center justify-between text-xs">
              <button
                disabled={page <= 1}
                onClick={() => fetchAnomalies(page - 1)}
                className="px-3 py-1.5 bg-white border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50 font-medium"
              >
                Previous Page
              </button>
              <span className="text-slate-600 font-medium">Page {page} of {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => fetchAnomalies(page + 1)}
                className="px-3 py-1.5 bg-white border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50 font-medium"
              >
                Next Page
              </button>
            </div>
          )}
        </div>
      )}

      {/* FORENSIC INVESTIGATION DOSSIER MODAL */}
      {selectedAnomaly && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full p-6 space-y-6 animate-in fade-in duration-200 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-200 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                    Anomaly Event #{selectedAnomaly.id}
                  </span>
                  <span className={`px-2.5 py-0.5 text-xs font-bold uppercase rounded ${
                    selectedAnomaly.severity === 'critical' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {selectedAnomaly.severity}
                  </span>
                  <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-mono font-semibold">
                    {selectedAnomaly.detection_method}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-900 mt-1">
                  {selectedAnomaly.building_name} ({selectedAnomaly.building_code})
                </h2>
                <p className="text-xs text-slate-500">
                  Observed Timestamp: {new Date(selectedAnomaly.timestamp).toLocaleString()}
                </p>
              </div>

              <button
                onClick={() => setSelectedAnomaly(null)}
                className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Status Workflow Selector Bar */}
            <div className="flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs">
              <span className="font-semibold text-slate-700">Investigation Lifecycle Status:</span>
              <div className="flex items-center gap-2">
                {(['open', 'investigating', 'resolved', 'dismissed'] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => handleStatusChange(selectedAnomaly.id, st)}
                    className={`px-3 py-1 rounded-md capitalize font-medium transition-colors ${
                      selectedAnomaly.status === st
                        ? 'bg-indigo-600 text-white shadow-xs font-bold'
                        : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            {/* Telemetry & Forensic Context Breakdown */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Quantitative Energy & Environmental Context
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-100 text-xs">
                <div>
                  <span className="text-slate-400 block">Observed Energy:</span>
                  <span className="font-bold text-indigo-700 text-base">{selectedAnomaly.actual_energy_kwh.toFixed(1)} kWh</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Expected Baseline:</span>
                  <span className="font-bold text-emerald-700 text-base">
                    {selectedAnomaly.predicted_energy_kwh != null ? `${selectedAnomaly.predicted_energy_kwh.toFixed(1)} kWh` : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Residual Deviation:</span>
                  <span className="font-bold text-rose-600 text-base">
                    {selectedAnomaly.residual_kwh != null ? `+${selectedAnomaly.residual_kwh.toFixed(1)} kWh` : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Percentage Surge:</span>
                  <span className="font-bold text-rose-600 text-base">
                    {selectedAnomaly.deviation_pct != null ? `+${selectedAnomaly.deviation_pct.toFixed(1)}%` : 'N/A'}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block">Outdoor Temperature:</span>
                  <span className="font-semibold text-slate-700">
                    {selectedAnomaly.outdoor_temp_c != null ? `${selectedAnomaly.outdoor_temp_c}°C` : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Occupancy Headcount:</span>
                  <span className="font-semibold text-slate-700">
                    {selectedAnomaly.occupancy_count != null ? `${selectedAnomaly.occupancy_count} people` : 'Unrecorded'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Day Type:</span>
                  <span className="font-semibold text-slate-700 capitalize">
                    {selectedAnomaly.day_type || 'working_day'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">HVAC Operating Status:</span>
                  <span className="font-semibold text-slate-700 capitalize">
                    {selectedAnomaly.hvac_status || 'normal'}
                  </span>
                </div>
              </div>
            </div>

            {/* Root-Cause Explanations */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Transparent Physical Root-Cause Explanations
              </h3>

              {(!selectedAnomaly.explanations || selectedAnomaly.explanations.length === 0) ? (
                <p className="text-xs text-slate-400 italic">No automated explanations attached to this event.</p>
              ) : (
                selectedAnomaly.explanations.map((expl) => (
                  <div key={expl.id} className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl text-xs space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <span className="font-bold text-amber-950 text-sm block">
                          {expl.primary_hypothesis}
                        </span>
                      </div>
                      <span className="px-2.5 py-0.5 text-xs font-bold bg-amber-200 text-amber-900 rounded uppercase shrink-0">
                        Confidence: {expl.confidence}
                      </span>
                    </div>

                    {expl.data_to_confirm && (
                      <div className="p-2.5 bg-white/80 rounded border border-amber-200 text-slate-700">
                        <strong className="text-amber-900 block mb-0.5">Physical Verification Checklist:</strong>
                        <span>{expl.data_to_confirm}</span>
                      </div>
                    )}

                    {expl.recommended_next_action && (
                      <div className="text-slate-700">
                        <strong className="text-slate-900">Recommended Next Step:</strong> {expl.recommended_next_action}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Actionable Operational Recommendations */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Prescriptive Operational Decision Support
              </h3>

              {(!selectedAnomaly.recommendations || selectedAnomaly.recommendations.length === 0) ? (
                <p className="text-xs text-slate-400 italic">No recommendations logged for this anomaly.</p>
              ) : (
                selectedAnomaly.recommendations.map((rec) => (
                  <div key={rec.id} className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3 text-xs">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded ${
                          rec.priority === 'critical' || rec.priority === 'high'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {rec.priority} Priority
                        </span>
                        <h4 className="text-sm font-bold text-slate-900 mt-1">{rec.title}</h4>
                      </div>

                      <select
                        value={rec.status}
                        onChange={(e) => handleRecommendationStatusChange(rec.id, e.target.value)}
                        className="px-2.5 py-1 text-xs border border-slate-300 rounded font-semibold bg-slate-50 text-slate-700 focus:outline-none"
                      >
                        <option value="open">Open</option>
                        <option value="investigating">Investigating</option>
                        <option value="resolved">Resolved</option>
                        <option value="dismissed">Dismissed</option>
                      </select>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg text-slate-700 space-y-1 border border-slate-100">
                      <p><strong className="text-slate-900">Prescribed Action:</strong> {rec.recommended_action}</p>
                      <p className="text-slate-500"><strong className="text-slate-700">Supporting Evidence:</strong> {rec.supporting_evidence}</p>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-1 text-slate-600">
                      <span className="flex items-center gap-1 font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded">
                        <User className="w-3.5 h-3.5" />
                        Assigned Role: {rec.responsible_role}
                      </span>

                      {rec.estimated_savings_kwh && (
                        <span className="text-emerald-700 font-bold">
                          Documented Savings: ~{rec.estimated_savings_kwh.toFixed(0)} kWh (≈ ₹{(rec.estimated_savings_kwh * 7.5).toFixed(0)})
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Modal Footer */}
            <div className="pt-4 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setSelectedAnomaly(null)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                Close Investigation Dossier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
