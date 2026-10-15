import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { DashboardOverview, DashboardAnalyticsResponse, Building } from '../types'
import {
  Zap, AlertTriangle, Building2, TrendingUp, ShieldCheck,
  Calendar, Layers, CheckCircle2, Clock
} from 'lucide-react'
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line,
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend
} from 'recharts'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#e11d48', // rose-600
  warning: '#f59e0b',  // amber-500
  normal: '#10b981',   // emerald-500
}

const CATEGORY_COLORS: Record<string, string> = {
  'Academic Block': '#4f46e5',     // indigo
  'Laboratory Block': '#06b6d4',   // cyan
  'Administrative Block': '#8b5cf6', // purple
  'Library': '#10b981',            // emerald
  'IT Block': '#3b82f6',           // blue
  'Workshop / Equipment Block': '#f97316', // orange
  'Other Campus Buildings': '#64748b', // slate
}

export const Overview: React.FC = () => {
  const [data, setData] = useState<DashboardOverview | null>(null)
  const [analytics, setAnalytics] = useState<DashboardAnalyticsResponse | null>(null)
  const [buildings, setBuildings] = useState<Building[]>([])
  const [selectedBuildingId, setSelectedBuildingId] = useState<number | undefined>(undefined)
  const [selectedRange, setSelectedRange] = useState<number>(168) // 7 days (168h), 14 days (336h), 30 days (720h)
  const [loading, setLoading] = useState(true)
  const [loadingAnalytics, setLoadingAnalytics] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initial Load: Overview metrics & Buildings list
  useEffect(() => {
    Promise.all([api.getDashboardOverview(), api.getBuildings(true)])
      .then(([overviewRes, bldRes]) => {
        setData(overviewRes)
        setBuildings(bldRes)
        if (bldRes.length > 0) {
          setSelectedBuildingId(bldRes[0].id)
        }
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message || 'Failed to load dashboard overview.')
        setLoading(false)
      })
  }, [])

  // Time-Series & Diurnal Fetch on building or range change
  useEffect(() => {
    if (!selectedBuildingId && buildings.length === 0) return
    setLoadingAnalytics(true)
    api.getDashboardTimeseries(selectedBuildingId, selectedRange)
      .then((res) => {
        setAnalytics(res)
        setLoadingAnalytics(false)
      })
      .catch((err) => {
        console.error('Failed to fetch time series analytics:', err)
        setLoadingAnalytics(false)
      })
  }, [selectedBuildingId, selectedRange, buildings])

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-2"></div>
        <p className="text-sm">Loading CIT campus intelligence dashboard...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-sm">
        <div className="font-bold flex items-center gap-2 mb-1">
          <AlertTriangle className="w-5 h-5 text-rose-600" />
          <span>Unable to connect to backend analytics service</span>
        </div>
        <p>{error || 'No overview data returned.'}</p>
        <p className="text-xs text-rose-600 mt-2">
          Ensure the FastAPI backend is running on port 8000 (<code>http://127.0.0.1:8000</code>).
        </p>
      </div>
    )
  }

  // Format Time-Series Data for Recharts
  const formattedTimeseries = (analytics?.timeseries || []).map((pt) => {
    const d = new Date(pt.timestamp)
    const timeLabel = `${d.getDate()}/${d.getMonth() + 1} ${String(d.getHours()).padStart(2, '0')}:00`
    return {
      time: timeLabel,
      fullDate: d.toLocaleString(),
      actual_kwh: pt.energy_kwh,
      predicted_kwh: pt.predicted_kwh ?? null,
      residual_kwh: pt.residual_kwh ?? null,
      anomaly_val: pt.is_anomaly ? pt.energy_kwh : null,
      is_anomaly: pt.is_anomaly,
      severity: pt.severity,
    }
  })

  // Format Diurnal Data for Recharts
  const formattedDiurnal = (analytics?.diurnal_profile || []).map((d) => ({
    hour: `${String(d.hour).padStart(2, '0')}:00`,
    working_day: d.working_day_avg,
    weekend: d.weekend_avg,
  }))

  // Format Severity Pie Chart Data
  const severityPieData = [
    { name: 'Critical', value: data.anomaly_severity_breakdown.critical, color: SEVERITY_COLORS.critical },
    { name: 'Warning', value: data.anomaly_severity_breakdown.warning, color: SEVERITY_COLORS.warning },
    { name: 'Normal', value: data.anomaly_severity_breakdown.normal, color: SEVERITY_COLORS.normal },
  ].filter((item) => item.value > 0)

  return (
    <div className="space-y-6">
      {/* Top Banner & Navigation Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
              Campus Intelligence Overview
            </span>
            <span className="text-xs text-slate-400 font-mono">Phase 10 Recharts Active</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mt-1">Campus Energy & Anomaly Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Interactive multi-building telemetry, AI expected baseline regression, and anomaly diagnostics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/energy-data"
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm transition-colors shadow-sm"
          >
            <Zap className="w-4 h-4" />
            Enter Reading
          </Link>
          <Link
            to="/buildings"
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg font-medium text-sm transition-colors"
          >
            <Building2 className="w-4 h-4" />
            Registry
          </Link>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Campus Energy</span>
            <Zap className="w-5 h-5 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {data.total_energy_kwh.toLocaleString(undefined, { maximumFractionDigits: 1 })}{' '}
            <span className="text-sm font-normal text-slate-500">kWh</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">{data.total_readings.toLocaleString()} hourly meter readings</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Estimated Cost</span>
            <TrendingUp className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 mt-2">
            ₹{data.total_cost_inr.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          <p className="text-xs text-slate-400 mt-1">Based on institutional commercial tariff</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Anomalies</span>
            <AlertTriangle className="w-5 h-5 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-600 mt-2">
            {data.active_anomalies_count}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {data.anomaly_severity_breakdown.critical} critical • {data.anomaly_severity_breakdown.warning} warning
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Monitored Facilities</span>
            <Building2 className="w-5 h-5 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {data.total_buildings}
          </div>
          <p className="text-xs text-slate-400 mt-1">Active CIT buildings & blocks</p>
        </div>
      </div>

      {/* Interactive Telemetry & Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
            <Layers className="w-4 h-4 text-indigo-600" />
            <span>Target Building:</span>
          </div>
          <select
            value={selectedBuildingId || ''}
            onChange={(e) => setSelectedBuildingId(Number(e.target.value))}
            className="px-3 py-1.5 text-xs font-semibold border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-800"
          >
            {buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.code} — {b.name}
              </option>
            ))}
          </select>
          {analytics && (
            <span className="text-xs text-slate-400 font-mono">
              (Viewing {analytics.building_name})
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            Window:
          </span>
          <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs">
            <button
              onClick={() => setSelectedRange(168)}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                selectedRange === 168 ? 'bg-white text-indigo-700 font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              7 Days (168h)
            </button>
            <button
              onClick={() => setSelectedRange(336)}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                selectedRange === 336 ? 'bg-white text-indigo-700 font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              14 Days (336h)
            </button>
            <button
              onClick={() => setSelectedRange(720)}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                selectedRange === 720 ? 'bg-white text-indigo-700 font-bold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              30 Days (720h)
            </button>
          </div>
        </div>
      </div>

      {/* CHART ROW 1: Actual vs Expected Time-Series & Diurnal Profile */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Actual vs Expected Consumption Area/Line Chart (2 cols) */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-800">Actual vs Expected Energy Baseline</h2>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-semibold">
                  RF Regressor v1.0
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Hourly telemetry (kWh) with expected load curve and flagged anomalous deviations.
              </p>
            </div>
            {loadingAnalytics && (
              <span className="text-xs text-indigo-600 font-medium animate-pulse">Updating...</span>
            )}
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={formattedTimeseries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickLine={false}
                  interval={Math.floor(formattedTimeseries.length / 7)}
                />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const p = payload[0].payload
                      return (
                        <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-md text-xs space-y-1">
                          <p className="font-bold text-slate-800">{p.fullDate}</p>
                          <div className="flex justify-between gap-4">
                            <span className="text-slate-500">Actual Observed:</span>
                            <span className="font-mono font-bold text-indigo-700">{p.actual_kwh} kWh</span>
                          </div>
                          {p.predicted_kwh !== null && (
                            <div className="flex justify-between gap-4">
                              <span className="text-slate-500">Expected Baseline:</span>
                              <span className="font-mono font-bold text-emerald-700">{p.predicted_kwh} kWh</span>
                            </div>
                          )}
                          {p.residual_kwh !== null && (
                            <div className="flex justify-between gap-4">
                              <span className="text-slate-500">Residual:</span>
                              <span className={`font-mono font-bold ${p.residual_kwh > 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                                {p.residual_kwh > 0 ? `+${p.residual_kwh}` : p.residual_kwh} kWh
                              </span>
                            </div>
                          )}
                          {p.is_anomaly && (
                            <div className="pt-1 border-t border-slate-100 flex items-center justify-between text-rose-600 font-bold">
                              <span>⚠ Anomaly Detected</span>
                              <span className="uppercase text-[10px] bg-rose-100 px-1.5 py-0.5 rounded">{p.severity}</span>
                            </div>
                          )}
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ paddingBottom: '8px', fontSize: '11px' }}
                />
                <Area
                  type="monotone"
                  dataKey="actual_kwh"
                  name="Actual (kWh)"
                  stroke="#4f46e5"
                  strokeWidth={2}
                  fill="url(#actualGradient)"
                />
                <Line
                  type="monotone"
                  dataKey="predicted_kwh"
                  name="Expected Baseline (kWh)"
                  stroke="#059669"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="anomaly_val"
                  name="Anomaly Flag"
                  stroke="#e11d48"
                  strokeWidth={0}
                  dot={{ r: 4, fill: '#e11d48', stroke: '#ffffff', strokeWidth: 1.5 }}
                  activeDot={{ r: 6, fill: '#e11d48' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Diurnal 24-Hour Profile Chart (1 col) */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-800">24h Diurnal Profile</h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Working day vs weekend load dynamics (kWh/h).
            </p>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={formattedDiurnal} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 9, fill: '#64748b' }}
                  tickLine={false}
                  interval={3}
                />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload
                      return (
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-md text-xs space-y-1">
                          <p className="font-bold text-slate-800">Hour {d.hour}</p>
                          <div className="flex justify-between gap-3 text-indigo-700">
                            <span>Working Day Avg:</span>
                            <span className="font-mono font-bold">{d.working_day} kWh</span>
                          </div>
                          <div className="flex justify-between gap-3 text-amber-600">
                            <span>Weekend / Off-Day:</span>
                            <span className="font-mono font-bold">{d.weekend} kWh</span>
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ paddingBottom: '8px', fontSize: '10px' }}
                />
                <Line
                  type="monotone"
                  dataKey="working_day"
                  name="Working Day"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  dot={{ r: 2 }}
                />
                <Line
                  type="monotone"
                  dataKey="weekend"
                  name="Weekend/Standby"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  dot={{ r: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* CHART ROW 2: Building Breakdown Bar Chart & Anomaly Severity Donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Building Consumption Bar Chart (2 cols) */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-800">Campus Facilities Consumption Comparison</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Total energy consumption (kWh) aggregated across monitored CIT buildings.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data.building_consumption}
                margin={{ top: 10, right: 10, left: -10, bottom: 25 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="building_code"
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickLine={false}
                  angle={-20}
                  textAnchor="end"
                />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const b = payload[0].payload
                      return (
                        <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-md text-xs space-y-1">
                          <p className="font-bold text-slate-800">{b.building_code} — {b.building_name}</p>
                          <p className="text-[11px] text-slate-500">{b.building_category}</p>
                          <div className="flex justify-between gap-4 pt-1">
                            <span>Total Energy:</span>
                            <span className="font-mono font-bold text-indigo-700">
                              {b.total_energy_kwh.toLocaleString()} kWh
                            </span>
                          </div>
                          <div className="flex justify-between gap-4">
                            <span>Average Hourly:</span>
                            <span className="font-mono font-bold text-slate-700">{b.avg_hourly_kwh} kWh</span>
                          </div>
                          <div className="flex justify-between gap-4">
                            <span>Anomalies Flagged:</span>
                            <span className={`font-mono font-bold ${b.anomaly_count > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                              {b.anomaly_count}
                            </span>
                          </div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Bar dataKey="total_energy_kwh" name="Total kWh" radius={[4, 4, 0, 0]}>
                  {data.building_consumption.map((entry) => (
                    <Cell
                      key={entry.building_id}
                      fill={CATEGORY_COLORS[entry.building_category] || '#4f46e5'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Anomaly Severity Donut Chart (1 col) */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-800">Anomaly Severity Profile</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Breakdown of detected operational deviations.
            </p>
          </div>

          <div className="h-48 w-full flex items-center justify-center">
            {severityPieData.length === 0 ? (
              <div className="text-center text-xs text-slate-400">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-1" />
                <span>Zero anomalies detected</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {severityPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload
                        return (
                          <div className="bg-white p-2 rounded border border-slate-200 shadow-sm text-xs font-semibold">
                            <span style={{ color: d.color }}>{d.name}:</span> {d.value} events
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-center text-xs">
            <div>
              <span className="text-[10px] text-slate-400 block uppercase font-semibold">Critical</span>
              <span className="font-bold text-rose-600 text-sm">{data.anomaly_severity_breakdown.critical}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block uppercase font-semibold">Warning</span>
              <span className="font-bold text-amber-500 text-sm">{data.anomaly_severity_breakdown.warning}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block uppercase font-semibold">Normal</span>
              <span className="font-bold text-emerald-600 text-sm">{data.anomaly_severity_breakdown.normal}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Buildings Consumption Benchmarks Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-800">Building Consumption Registry Benchmarks</h2>
          <span className="text-xs text-slate-400 font-mono">Aggregated DB Metrics</span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-semibold">
              <tr>
                <th className="px-6 py-3 text-left">Building Code & Name</th>
                <th className="px-6 py-3 text-left">Category</th>
                <th className="px-6 py-3 text-right">Readings Logged</th>
                <th className="px-6 py-3 text-right">Total Energy (kWh)</th>
                <th className="px-6 py-3 text-right">Avg Hourly (kWh)</th>
                <th className="px-6 py-3 text-right">Anomalies Detected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {data.building_consumption.map((b) => (
                <tr key={b.building_id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-6 py-3">
                    <span className="font-mono font-bold text-slate-900 mr-2">{b.building_code}</span>
                    <span className="text-slate-600">{b.building_name}</span>
                  </td>
                  <td className="px-6 py-3">
                    <span
                      className="inline-block px-2 py-0.5 text-xs font-medium rounded text-white"
                      style={{ backgroundColor: CATEGORY_COLORS[b.building_category] || '#4f46e5' }}
                    >
                      {b.building_category}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-right font-mono">{b.reading_count.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right font-mono font-semibold">
                    {b.total_energy_kwh.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                  </td>
                  <td className="px-6 py-3 text-right font-mono">
                    {b.avg_hourly_kwh.toFixed(2)}
                  </td>
                  <td className="px-6 py-3 text-right">
                    {b.anomaly_count > 0 ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                        {b.anomaly_count} flagged
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                        Clean
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Alerts Feed */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-800">Recent Detected Anomaly Events</h2>
            <p className="text-xs text-slate-500">Dual-method residual and Isolation Forest flags requiring attention</p>
          </div>
          <Link to="/anomalies" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
            Open Anomaly Center →
          </Link>
        </div>
        <div className="divide-y divide-slate-100">
          {data.recent_alerts.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-sm">No recent anomaly events recorded.</div>
          ) : (
            data.recent_alerts.map((alert) => (
              <div key={alert.anomaly_id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-800 text-sm">{alert.building_code}</span>
                    <span className="text-xs text-slate-500">{alert.building_name}</span>
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-full uppercase ${
                      alert.severity === 'critical' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {alert.severity}
                    </span>
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                      {alert.detection_method}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-3">
                    <span>Observed: <strong className="text-slate-700">{alert.actual_energy_kwh} kWh</strong></span>
                    {alert.predicted_energy_kwh && (
                      <span>Expected: <strong className="text-slate-700">{alert.predicted_energy_kwh.toFixed(1)} kWh</strong></span>
                    )}
                    {alert.deviation_pct && (
                      <span className="text-rose-600 font-semibold">+{alert.deviation_pct.toFixed(1)}% deviation</span>
                    )}
                    <span>Timestamp: {new Date(alert.timestamp).toLocaleString()}</span>
                  </div>
                </div>

                <div>
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-md uppercase ${
                    alert.status === 'open' ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {alert.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Academic Prototype Notice */}
      <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-xl text-xs text-indigo-900 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Phase 10 Interactive Recharts Visualizations:</span>{' '}
          All charts dynamically re-render upon changing target facility or temporal window. Telemetry is plotted with actual consumption areas, expected baseline regression lines, and high-visibility anomaly markers.
        </div>
      </div>
    </div>
  )
}
