import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { Recommendation } from '../types'
import {
  Lightbulb, CheckCircle2, User, DollarSign,
  TrendingDown, ShieldCheck, Search, RefreshCw, AlertCircle, Leaf
} from 'lucide-react'

export const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  // Filters
  const [priorityFilter, setPriorityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')

  const fetchRecommendations = async (p = 1) => {
    setLoading(true)
    try {
      const res = await api.getRecommendations(
        p,
        15,
        priorityFilter || undefined,
        statusFilter || undefined
      )
      setRecommendations(res.items)
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
    fetchRecommendations(1)
  }, [priorityFilter, statusFilter])

  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      await api.updateRecommendationStatus(id, newStatus)
      setRecommendations((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: newStatus as any } : r))
      )
    } catch (err) {
      alert('Failed to update recommendation status.')
    }
  }

  // Filter by role on client side
  const filteredRecs = recommendations.filter((r) => {
    if (!roleFilter) return true
    return r.responsible_role.toLowerCase().includes(roleFilter.toLowerCase())
  })

  // Aggregate metrics
  const totalSavingsKwh = recommendations
    .filter((r) => r.status === 'open' || r.status === 'investigating')
    .reduce((acc, r) => acc + (r.estimated_savings_kwh || 0), 0)

  const estimatedCostRecoveryInr = totalSavingsKwh * 7.5 // ₹7.50/kWh institutional tariff
  const criticalCount = recommendations.filter((r) => r.priority === 'critical' || r.priority === 'high').length
  const resolvedCount = recommendations.filter((r) => r.status === 'resolved').length

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <Lightbulb className="w-3.5 h-3.5" />
              Decision Support System
            </span>
            <span className="text-xs text-slate-400 font-mono">CIT Energy Stewardship</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mt-1">Operational Recommendations Workspace</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Prescriptive facilities management workflows, responsible campus roles, and verified financial savings estimates.
          </p>
        </div>

        <button
          onClick={() => fetchRecommendations(page)}
          className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-sm font-medium transition-colors shadow-sm self-start md:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh Registry
        </button>
      </div>

      {/* KPI Financial & Operations Savings Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Potential Energy Recovery</span>
            <TrendingDown className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            ~{totalSavingsKwh.toLocaleString(undefined, { maximumFractionDigits: 0 })}{' '}
            <span className="text-sm font-normal text-slate-500">kWh</span>
          </div>
          <span className="text-xs text-slate-400">Across open actionable tasks</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Cost Reduction Potential</span>
            <DollarSign className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 mt-1">
            ₹{estimatedCostRecoveryInr.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          <span className="text-xs text-slate-400">At ₹7.50 / kWh campus tariff</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">High/Critical Priority</span>
            <AlertCircle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-2xl font-bold text-rose-600 mt-1">{criticalCount}</div>
          <span className="text-xs text-slate-400">Immediate action required</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Resolved Workflows</span>
            <CheckCircle2 className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-blue-700 mt-1">{resolvedCount}</div>
          <span className="text-xs text-slate-400">Verified and mitigated</span>
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
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
          >
            <option value="">All Priorities</option>
            <option value="critical">Critical Priority</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
          >
            <option value="">All Workflow Statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
          >
            <option value="">All Assigned Campus Roles</option>
            <option value="Electrical">Electrical Supervisor</option>
            <option value="HVAC">HVAC Technician</option>
            <option value="Manager">Energy Manager</option>
            <option value="Estate">Estate Officer</option>
          </select>
        </div>

        <span className="text-xs text-slate-500">
          Showing {filteredRecs.length} of {total} operational recommendations
        </span>
      </div>

      {/* Recommendations Cards Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-2"></div>
          <p className="text-sm">Loading operational decision recommendations...</p>
        </div>
      ) : filteredRecs.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-2">
          <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
          <p className="font-semibold text-slate-800 text-base">No active recommendations matching filters</p>
          <p className="text-xs text-slate-400">Campus facilities systems are operating according to efficiency guidelines.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRecs.map((rec) => (
            <div
              key={rec.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4 flex flex-col justify-between hover:border-indigo-300 transition-colors"
            >
              <div className="space-y-3">
                {/* Header Tag */}
                <div className="flex items-start justify-between gap-2">
                  <span
                    className={`px-2.5 py-1 text-xs font-bold uppercase rounded ${
                      rec.priority === 'critical' || rec.priority === 'high'
                        ? 'bg-rose-100 text-rose-800 border border-rose-200'
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {rec.priority} Priority
                  </span>

                  <span className="font-mono text-xs text-slate-400">
                    {rec.building_code ? `${rec.building_code}` : `Anomaly #${rec.anomaly_event_id}`}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 leading-snug">{rec.title}</h3>

                {/* Prescribed Actions and Evidence */}
                <div className="p-3.5 bg-slate-50 rounded-lg text-xs space-y-2 border border-slate-100">
                  <p className="text-slate-700">
                    <strong className="text-slate-900 block mb-0.5">Actionable Directive:</strong>
                    {rec.recommended_action}
                  </p>
                  <p className="text-slate-500">
                    <strong className="text-slate-700 block mb-0.5">Supporting Evidence:</strong>
                    {rec.supporting_evidence}
                  </p>
                </div>

                {/* Follow up verification */}
                {rec.follow_up_verification && (
                  <div className="text-xs p-2.5 bg-emerald-50/60 rounded border border-emerald-100 text-emerald-900">
                    <strong className="block mb-0.5 font-bold">Verification Checklist:</strong>
                    <span>{rec.follow_up_verification}</span>
                  </div>
                )}
              </div>

              {/* Card Footer: Role, Savings & Status Toggle */}
              <div className="pt-3 border-t border-slate-100 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="inline-flex items-center gap-1.5 font-semibold bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded">
                    <User className="w-3.5 h-3.5" />
                    {rec.responsible_role}
                  </span>

                  {rec.estimated_savings_kwh && (
                    <span className="text-emerald-700 font-bold">
                      Est. Savings: ~{rec.estimated_savings_kwh.toFixed(0)} kWh (≈ ₹{(rec.estimated_savings_kwh * 7.5).toFixed(0)})
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-slate-400 font-medium">Lifecycle Status:</span>
                  <div className="flex items-center gap-2">
                    {rec.status === 'resolved' && (
                      <Link
                        to="/sustainability"
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 px-2 py-0.5 rounded border border-emerald-200 transition-colors"
                        title="View or verify in Campus Sustainability Ledger"
                      >
                        <Leaf className="w-3 h-3 text-emerald-600" />
                        Verify Impact
                      </Link>
                    )}
                    <select
                      value={rec.status}
                      onChange={(e) => handleStatusChange(rec.id, e.target.value)}
                      className={`px-3 py-1 text-xs border rounded font-semibold focus:outline-none ${
                        rec.status === 'resolved'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                          : rec.status === 'investigating'
                          ? 'bg-amber-50 text-amber-800 border-amber-300'
                          : 'bg-white text-slate-700 border-slate-300'
                      }`}
                    >
                      <option value="open">Open</option>
                      <option value="investigating">Investigating</option>
                      <option value="resolved">Resolved</option>
                      <option value="dismissed">Dismissed</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="p-4 bg-white rounded-xl border border-slate-200 flex items-center justify-between text-xs">
          <button
            disabled={page <= 1}
            onClick={() => fetchRecommendations(page - 1)}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50 font-medium"
          >
            Previous
          </button>
          <span className="font-medium text-slate-600">Page {page} of {totalPages}</span>
          <button
            disabled={page >= totalPages}
            onClick={() => fetchRecommendations(page + 1)}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50 font-medium"
          >
            Next
          </button>
        </div>
      )}

      {/* Educational Academic Note */}
      <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl text-xs text-emerald-950 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Phase 11 Decision Support Integration:</span>{' '}
          All recommendations are generated deterministically by the rule-based explainability engine in Phase 7. Modifying status synchronizes directly with the PostgreSQL/SQLite `recommendations` table, enabling facilities managers to track and verify energy savings.
        </div>
      </div>
    </div>
  )
}
