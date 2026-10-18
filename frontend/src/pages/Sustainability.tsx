import { useState, useEffect } from 'react'
import {
  Leaf, TrendingDown, DollarSign, Award,
  Calendar, Building2, Trees, Car, Home,
  AlertCircle, FileText,
  Plus, RefreshCw, Info, Download, ShieldCheck,
  ArrowUpRight, BarChart3
} from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, Cell
} from 'recharts'
import { api } from '../services/api'
import type {
  SustainabilitySummary, BuildingSustainability,
  SustainabilityTrends, CarbonFootprint,
  SustainabilityTarget, SustainabilityVerification,
  Building, SustainabilityReport
} from '../types'

export function Sustainability() {
  // State
  const [summary, setSummary] = useState<SustainabilitySummary | null>(null)
  const [buildings, setBuildings] = useState<BuildingSustainability[]>([])
  const [allBuildings, setAllBuildings] = useState<Building[]>([])
  const [trends, setTrends] = useState<SustainabilityTrends | null>(null)
  const [carbonFootprint, setCarbonFootprint] = useState<CarbonFootprint | null>(null)
  const [targets, setTargets] = useState<SustainabilityTarget[]>([])
  const [verifications, setVerifications] = useState<SustainabilityVerification[]>([])
  const [report, setReport] = useState<SustainabilityReport | null>(null)

  // Filters
  const [selectedBuildingId, setSelectedBuildingId] = useState<number | undefined>(undefined)
  const [granularity, setGranularity] = useState<'daily' | 'hourly'>('daily')
  const [dateRange, setDateRange] = useState<string>('all') // '7d', '14d', '30d', 'all'
  
  // UI Controls
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'buildings' | 'emissions' | 'targets' | 'verification'>('overview')
  const [showTargetModal, setShowTargetModal] = useState<boolean>(false)
  const [showReportModal, setShowReportModal] = useState<boolean>(false)
  const [verifyingId, setVerifyingId] = useState<number | null>(null)
  const [selectedVerification, setSelectedVerification] = useState<SustainabilityVerification | null>(null)

  // Target Form
  const [newTarget, setNewTarget] = useState({
    name: '',
    description: '',
    building_id: undefined as number | undefined,
    metric_type: 'electricity_kwh',
    target_reduction_pct: 10.0,
    baseline_value: 50000.0,
    target_completion_date: new Date(Date.now() + 90 * 86400000).toISOString().split('T')[0]
  })

  // Calculate ISO dates from quick range
  const getDateBounds = (range: string) => {
    if (range === 'all') return { start: undefined, end: undefined }
    const end = new Date()
    const start = new Date()
    if (range === '7d') start.setDate(end.getDate() - 7)
    if (range === '14d') start.setDate(end.getDate() - 14)
    if (range === '30d') start.setDate(end.getDate() - 30)
    return { start: start.toISOString(), end: end.toISOString() }
  }

  // Load all data
  const loadData = async () => {
    setLoading(true)
    setError(null)
    const { start, end } = getDateBounds(dateRange)

    try {
      const [sumRes, bldRes, trendRes, carbRes, tgtRes, verRes, allBldRes] = await Promise.all([
        api.getSustainabilitySummary(start, end, selectedBuildingId),
        api.getBuildingSustainability(start, end),
        api.getSustainabilityTrends(selectedBuildingId, start, end, granularity),
        api.getCarbonFootprint(start, end),
        api.getSustainabilityTargets(),
        api.getSustainabilityVerifications(),
        api.getBuildings(true)
      ])

      setSummary(sumRes)
      setBuildings(bldRes)
      setTrends(trendRes)
      setCarbonFootprint(carbRes)
      setTargets(tgtRes)
      setVerifications(verRes)
      setAllBuildings(allBldRes)
    } catch (err: any) {
      console.error('Failed to load sustainability data:', err)
      setError(err.message || 'Failed to communicate with sustainability intelligence API.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [selectedBuildingId, granularity, dateRange])

  // Handle Verify Action
  const handleVerify = async (recId: number) => {
    setVerifyingId(recId)
    try {
      const res = await api.verifyRecommendationImpact(recId)
      setSelectedVerification(res)
      await loadData()
    } catch (err: any) {
      alert('Verification assessment failed: ' + err.message)
    } finally {
      setVerifyingId(null)
    }
  }

  // Handle Target Creation
  const handleCreateTarget = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const now = new Date()
      const baseStart = new Date(now.getTime() - 30 * 86400000).toISOString()
      const baseEnd = now.toISOString()
      const compDate = new Date(newTarget.target_completion_date).toISOString()

      await api.createSustainabilityTarget({
        name: newTarget.name,
        description: newTarget.description,
        building_id: newTarget.building_id || undefined,
        metric_type: newTarget.metric_type,
        target_reduction_pct: Number(newTarget.target_reduction_pct),
        baseline_period_start: baseStart,
        baseline_period_end: baseEnd,
        baseline_value: Number(newTarget.baseline_value),
        target_completion_date: compDate
      })

      setShowTargetModal(false)
      setNewTarget({
        name: '',
        description: '',
        building_id: undefined,
        metric_type: 'electricity_kwh',
        target_reduction_pct: 10.0,
        baseline_value: 50000.0,
        target_completion_date: new Date(Date.now() + 90 * 86400000).toISOString().split('T')[0]
      })
      loadData()
    } catch (err: any) {
      alert('Failed to register sustainability target: ' + err.message)
    }
  }

  // Handle Generate Report
  const handleOpenReport = async () => {
    const { start, end } = getDateBounds(dateRange)
    try {
      const rep = await api.getSustainabilityReport(start, end)
      setReport(rep)
      setShowReportModal(true)
    } catch (err: any) {
      alert('Failed to generate report: ' + err.message)
    }
  }

  // Export report as JSON/CSV
  const handleDownloadReportCSV = () => {
    if (!buildings.length) return
    const headers = ['Building Code', 'Building Name', 'Category', 'Floor Area (m2)', 'Total kWh', 'Energy Intensity (kWh/m2)', 'Carbon Emissions (kg CO2e)', 'Verified Savings (kWh)']
    const rows = buildings.map(b => [
      b.code,
      `"${b.name}"`,
      `"${b.category}"`,
      b.floor_area_sqm,
      b.total_energy_kwh,
      b.energy_intensity_kwh_sqm,
      b.emissions_kg_co2e,
      b.verified_savings_kwh
    ])
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `CIT_Sustainability_Audit_${new Date().toISOString().split('T')[0]}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const categoryColors: Record<string, string> = {
    'Academic Block': '#4f46e5',
    'Laboratory Block': '#06b6d4',
    'IT Block': '#8b5cf6',
    'Library': '#10b981',
    'Workshop / Equipment Block': '#f59e0b',
    'Main Block': '#3b82f6',
    'Other Campus Buildings': '#64748b'
  }

  return (
    <div className="space-y-6">
      {/* Top Header & Context */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-lg bg-emerald-600 text-white flex items-center justify-center shadow-xs">
              <Leaf className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Campus Sustainability Intelligence</h1>
                <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full font-semibold border border-emerald-200">
                  Scope 2 Electricity Decarbonization
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Coimbatore Institute of Technology • Central Electricity Authority (CEA) India v19 Factor Baseline
              </p>
            </div>
          </div>
        </div>

        {/* Global Action Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Facility Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs">
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedBuildingId || ''}
              onChange={(e) => setSelectedBuildingId(e.target.value ? Number(e.target.value) : undefined)}
              className="bg-transparent border-none text-slate-700 font-medium focus:outline-none cursor-pointer text-xs"
            >
              <option value="">All Campus Facilities (6 Monitored)</option>
              {allBuildings.map(b => (
                <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
              ))}
            </select>
          </div>

          {/* Date Range Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="bg-transparent border-none text-slate-700 font-medium focus:outline-none cursor-pointer text-xs"
            >
              <option value="all">Full Baseline Period (Aug–Sep 2026)</option>
              <option value="30d">Last 30 Days</option>
              <option value="14d">Last 14 Days</option>
              <option value="7d">Last 7 Days</option>
            </select>
          </div>

          {/* Action Buttons */}
          <button
            onClick={loadData}
            title="Refresh Telemetry"
            className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleOpenReport}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-medium text-xs hover:bg-emerald-700 shadow-xs transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            Audit Report
          </button>
        </div>
      </div>

      {/* Synthetic Data Disclaimer Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 flex items-start gap-3 text-xs text-amber-900">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-amber-800">Academic Decision Support & Synthetic Baseline Provenance:</span>
          <p className="text-amber-700 leading-relaxed">
            Campus baseline telemetry is modeled via synthetic hourly load curves simulating CIT Coimbatore lecture blocks, IT clusters, and research labs. 
            All carbon calculations use the official <strong>Central Electricity Authority (CEA) of India Baseline v19</strong> factor of <strong>0.716 kg CO₂e/kWh</strong> for the Southern Regional Grid.
          </p>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-slate-200 gap-6 text-sm font-medium">
        {[
          { key: 'overview', label: 'Sustainability Overview', icon: Leaf },
          { key: 'buildings', label: 'Facility Intensity Benchmarks', icon: Building2 },
          { key: 'emissions', label: 'Carbon Footprint & Scope 2', icon: Trees },
          { key: 'targets', label: 'Decarbonization Targets', icon: Award },
          { key: 'verification', label: 'Verified Savings Ledger', icon: ShieldCheck }
        ].map(tab => {
          const Icon = tab.icon
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 pb-3 pt-1 border-b-2 font-medium text-xs sm:text-sm transition-colors cursor-pointer ${
                isActive
                  ? 'border-emerald-600 text-emerald-700'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Verification Feedback Banner */}
      {selectedVerification && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-900 flex items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              Audit completed for: <strong>{selectedVerification.recommendation_title || `Directive #${selectedVerification.recommendation_id}`}</strong> — 
              Status: <strong className="uppercase">{selectedVerification.verification_status}</strong> ({selectedVerification.observed_reduction_pct}% observed reduction, ₹{selectedVerification.cost_savings_inr} saved).
            </span>
          </div>
          <button
            onClick={() => setSelectedVerification(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-xs text-red-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 animate-pulse">
          {[1, 2, 3, 4].map(n => (
            <div key={n} className="bg-white p-5 rounded-xl border border-slate-200 h-28"></div>
          ))}
        </div>
      )}

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && summary && (
        <div className="space-y-6">
          {/* KPI Cards Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Total Carbon Emissions */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs relative overflow-hidden">
              <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
                <span>Carbon Emissions (Scope 2)</span>
                <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <Trees className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-2.5">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold text-slate-900">{summary.total_emissions_tonnes_co2e.toLocaleString()}</span>
                  <span className="text-xs font-semibold text-slate-500">t CO₂e</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  {summary.total_emissions_kg_co2e.toLocaleString()} kg @ {summary.emissions_factor_info.emission_factor} kg/kWh
                </p>
              </div>
              <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-emerald-700">
                <span>CEA v19 Tamil Nadu Factor</span>
                <span className="font-semibold">0.716 kg/kWh</span>
              </div>
            </div>

            {/* Card 2: Energy Consumption */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs relative overflow-hidden">
              <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
                <span>Campus Electricity</span>
                <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <BarChart3 className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-2.5">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold text-slate-900">{summary.total_energy_kwh.toLocaleString()}</span>
                  <span className="text-xs font-semibold text-slate-500">kWh</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Modeled utility cost: ₹{summary.total_cost_inr.toLocaleString()} (@ ₹7.50/kWh)
                </p>
              </div>
              <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-600">
                <span>Active Facilities</span>
                <span className="font-semibold text-slate-900">6 Monitored</span>
              </div>
            </div>

            {/* Card 3: Energy Intensity */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs relative overflow-hidden">
              <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
                <span>Energy Intensity</span>
                <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                  <TrendingDown className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-2.5">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold text-slate-900">{summary.average_energy_intensity_kwh_sqm}</span>
                  <span className="text-xs font-semibold text-slate-500">kWh/m²</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Floor-area normalized benchmark across CIT campus
                </p>
              </div>
              <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-600">
                <span>Normalization</span>
                <span className="font-semibold text-slate-900">Gross Floor Area</span>
              </div>
            </div>

            {/* Card 4: Verified vs Potential Savings */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs relative overflow-hidden">
              <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
                <span>Savings & Decarbonization</span>
                <div className="w-7 h-7 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center">
                  <DollarSign className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-2.5">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold text-teal-700">₹{summary.verified_savings_inr.toLocaleString()}</span>
                  <span className="text-xs font-semibold text-slate-500">verified</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  {summary.verified_savings_kwh} kWh ({summary.verified_emissions_reduction_kg_co2e} kg CO₂e avoided)
                </p>
              </div>
              <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Potential Pipeline</span>
                <span className="font-semibold text-slate-700">₹{summary.potential_savings_inr.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Timeseries Trend Area Chart: Actual vs Baseline vs Carbon */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
              <div>
                <h2 className="text-base font-bold text-slate-900">Campus Energy, Baseline & Carbon Emission Trends</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Comparing actual electricity consumption against model expected baseline and estimated Scope 2 carbon profile
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs">
                  <button
                    onClick={() => setGranularity('daily')}
                    className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                      granularity === 'daily' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    Daily
                  </button>
                  <button
                    onClick={() => setGranularity('hourly')}
                    className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                      granularity === 'hourly' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    Hourly
                  </button>
                </div>
              </div>
            </div>

            {trends && trends.trends.length > 0 ? (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trends.trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.25}/>
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.0}/>
                      </linearGradient>
                      <linearGradient id="baselineGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(val) => {
                        const d = new Date(val)
                        return granularity === 'daily'
                          ? d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                          : `${d.getHours()}:00`
                      }}
                      stroke="#94a3b8"
                      fontSize={11}
                    />
                    <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(val) => `${val} kWh`} />
                    <Tooltip
                      content={({ active, payload, label }) => {
                        if (active && payload && payload.length) {
                          const p = payload[0].payload
                          const dateVal = label || p.timestamp || new Date().toISOString()
                          return (
                            <div className="bg-slate-900 text-white p-3 rounded-lg text-xs shadow-lg space-y-1">
                              <p className="font-semibold text-slate-300">
                                {new Date(dateVal).toLocaleString(undefined, {
                                  month: 'short', day: 'numeric', hour: granularity === 'hourly' ? '2-digit' : undefined
                                })}
                              </p>
                              <div className="flex justify-between gap-4">
                                <span className="text-indigo-300">Actual Electricity:</span>
                                <span className="font-bold">{p.actual_kwh} kWh</span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-emerald-300">Expected Baseline:</span>
                                <span>{p.baseline_kwh} kWh</span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-slate-400">Carbon Footprint:</span>
                                <span>{p.emissions_kg_co2e} kg CO₂e</span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-amber-300">Energy Intensity:</span>
                                <span>{p.energy_intensity_kwh_sqm} kWh/m²</span>
                              </div>
                            </div>
                          )
                        }
                        return null
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Area type="monotone" dataKey="actual_kwh" name="Actual Consumption (kWh)" stroke="#4f46e5" fillOpacity={1} fill="url(#actualGrad)" strokeWidth={2} />
                    <Area type="monotone" dataKey="baseline_kwh" name="Expected Baseline (kWh)" stroke="#10b981" fillOpacity={1} fill="url(#baselineGrad)" strokeWidth={2} strokeDasharray="3 3" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-400 text-xs">
                No timeseries records found for the selected filter parameters.
              </div>
            )}
          </div>

          {/* Quick Facility Energy Intensity Rankings */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">Facility Energy Intensity Benchmarking (kWh/m²)</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Normalized consumption per square metre enables fair comparisons across lecture theatres, laboratories, and computer centers
                </p>
              </div>
              <button
                onClick={() => setActiveTab('buildings')}
                className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
              >
                View Full Audit Table <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={buildings} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="code" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(val) => `${val} kWh/m²`} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const b = payload[0].payload
                        return (
                          <div className="bg-slate-900 text-white p-3 rounded-lg text-xs shadow-lg space-y-1">
                            <p className="font-semibold text-slate-200">{b.name} ({b.code})</p>
                            <p className="text-slate-400 text-[11px]">{b.category} • {b.floor_area_sqm} m²</p>
                            <div className="flex justify-between gap-4 mt-2">
                              <span className="text-indigo-300">Energy Intensity:</span>
                              <span className="font-bold">{b.energy_intensity_kwh_sqm} kWh/m²</span>
                            </div>
                            <div className="flex justify-between gap-4">
                              <span className="text-slate-400">Total Consumption:</span>
                              <span>{b.total_energy_kwh.toLocaleString()} kWh</span>
                            </div>
                            <div className="flex justify-between gap-4">
                              <span className="text-emerald-300">Carbon Footprint:</span>
                              <span>{(b.emissions_kg_co2e / 1000).toFixed(2)} t CO₂e</span>
                            </div>
                          </div>
                        )
                      }
                      return null
                    }}
                  />
                  <Bar dataKey="energy_intensity_kwh_sqm" name="Energy Intensity (kWh/m²)" radius={[4, 4, 0, 0]}>
                    {buildings.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={categoryColors[entry.category] || '#4f46e5'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: FACILITY INTENSITY BENCHMARKS TABLE */}
      {activeTab === 'buildings' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Campus Facility Sustainability Benchmarks</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Audited electricity, normalized floor-area energy intensity, carbon output, and verified savings ledger
                </p>
              </div>
              <button
                onClick={handleDownloadReportCSV}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                <Download className="w-3.5 h-3.5" />
                Export CSV Ledger
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Facility Code & Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-right">Floor Area</th>
                    <th className="py-3 px-4 text-right">Total Electricity</th>
                    <th className="py-3 px-4 text-right">Energy Intensity</th>
                    <th className="py-3 px-4 text-right">Carbon Footprint</th>
                    <th className="py-3 px-4 text-right">Baseline Expected</th>
                    <th className="py-3 px-4 text-right">Deviation</th>
                    <th className="py-3 px-4 text-right">Verified Savings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {buildings.map(b => (
                    <tr key={b.building_id} className="hover:bg-slate-50/75 transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-slate-900">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: categoryColors[b.category] || '#64748b' }}></span>
                          <span>{b.code}</span>
                          <span className="font-normal text-slate-500 text-[11px] truncate max-w-[150px]">{b.name}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-100 text-slate-700">
                          {b.category}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right text-slate-600 font-mono">{b.floor_area_sqm.toLocaleString()} m²</td>
                      <td className="py-3.5 px-4 text-right font-semibold text-slate-900 font-mono">{b.total_energy_kwh.toLocaleString()} kWh</td>
                      <td className="py-3.5 px-4 text-right font-bold text-indigo-700 font-mono">{b.energy_intensity_kwh_sqm} kWh/m²</td>
                      <td className="py-3.5 px-4 text-right text-slate-700 font-mono">{(b.emissions_kg_co2e / 1000).toFixed(2)} t CO₂e</td>
                      <td className="py-3.5 px-4 text-right text-slate-500 font-mono">{b.baseline_expected_kwh.toLocaleString()} kWh</td>
                      <td className="py-3.5 px-4 text-right font-mono">
                        <span className={`px-2 py-0.5 rounded-full font-semibold text-[10px] ${
                          b.deviation_pct > 15
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : b.deviation_pct > 5
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}>
                          {b.deviation_pct > 0 ? `+${b.deviation_pct}%` : `${b.deviation_pct}%`}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-bold text-emerald-700 font-mono">
                        {b.verified_savings_kwh > 0 ? `${b.verified_savings_kwh} kWh` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 leading-relaxed">
              <strong>Benchmarking Note:</strong> Energy Intensity ($kWh/m^2$) is the standard metric recognized by the Bureau of Energy Efficiency (BEE) India. 
              Facilities with specialized cooling or dense equipment (e.g., Computer Center `CIT-IT`) naturally operate at higher base intensity than standard lecture classrooms.
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CARBON FOOTPRINT & SCOPE 2 */}
      {activeTab === 'emissions' && carbonFootprint && (
        <div className="space-y-6">
          {/* Emissions Scope Header Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
              <div>
                <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">Accounting Standard</span>
                <h2 className="text-lg font-bold text-slate-900 mt-1">Scope 2 (Location-Based) Electricity Emissions</h2>
                <p className="text-xs text-slate-500 mt-1 max-w-2xl">
                  {carbonFootprint.scope_boundary_notice}
                </p>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-right">
                <span className="text-xs text-emerald-800 font-medium">Total Campus Footprint</span>
                <div className="text-3xl font-black text-emerald-900 mt-0.5">{carbonFootprint.total_emissions_tonnes_co2e}</div>
                <span className="text-[11px] text-emerald-700 font-semibold">tonnes CO₂e</span>
              </div>
            </div>

            {/* Environmental Equivalencies Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6">
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                  <Trees className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500">Tree Carbon Absorption</span>
                  <div className="text-lg font-bold text-slate-900">
                    {carbonFootprint.equivalencies.tree_seedlings_10_years.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-slate-400">Tree seedlings grown for 10 yrs</span>
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                  <Car className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500">Passenger Vehicle Travel</span>
                  <div className="text-lg font-bold text-slate-900">
                    {carbonFootprint.equivalencies.passenger_vehicle_km_avoided.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-slate-400">Kilometers driven equivalent</span>
                </div>
              </div>

              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                  <Home className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-slate-500">Urban Residential Power</span>
                  <div className="text-lg font-bold text-slate-900">
                    {carbonFootprint.equivalencies.indian_households_monthly_power.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-slate-400">Indian households monthly power</span>
                </div>
              </div>
            </div>
          </div>

          {/* Grid Emission Factor Provenance Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 mb-3">Regional Grid Emission Factor Configuration</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Emission Factor</span>
                <span className="font-bold text-slate-900 text-sm mt-0.5 block">{carbonFootprint.emissions_factor.emission_factor} kg CO₂e/kWh</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Authoritative Source</span>
                <span className="font-medium text-slate-800 mt-0.5 block truncate" title={carbonFootprint.emissions_factor.source_name}>
                  {carbonFootprint.emissions_factor.source_name}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Applicable Regional Grid</span>
                <span className="font-medium text-slate-800 mt-0.5 block">{carbonFootprint.emissions_factor.applicable_region}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Effective Horizon</span>
                <span className="font-medium text-slate-800 mt-0.5 block">{carbonFootprint.emissions_factor.effective_date}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: DECARBONIZATION TARGETS */}
      {activeTab === 'targets' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Institutional Sustainability Targets</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Target reduction goals calibrated against pre-intervention baseline periods
              </p>
            </div>
            <button
              onClick={() => setShowTargetModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-medium text-xs hover:bg-emerald-700 shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Configure Target
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {targets.map(t => {
              const statusColors: Record<string, string> = {
                'in_progress': 'bg-blue-50 text-blue-700 border-blue-200',
                'achieved': 'bg-emerald-50 text-emerald-700 border-emerald-200',
                'at_risk': 'bg-rose-50 text-rose-700 border-rose-200',
                'expired': 'bg-slate-100 text-slate-700 border-slate-200'
              }

              return (
                <div key={t.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-slate-900 text-sm">{t.name}</h3>
                      <p className="text-xs text-slate-500 mt-0.5">{t.description || 'Target reduction initiative.'}</p>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider ${statusColors[t.status] || 'bg-slate-100 text-slate-600'}`}>
                      {t.status.replace('_', ' ')}
                    </span>
                  </div>

                  {/* Target Progress Bar */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-600 font-medium">Reduction Progress</span>
                      <span className="font-bold text-slate-900">{t.current_measured_progress_pct}%</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                      <div
                        className={`h-2.5 rounded-full transition-all duration-500 ${
                          t.status === 'achieved' ? 'bg-emerald-500' : t.status === 'at_risk' ? 'bg-rose-500' : 'bg-indigo-600'
                        }`}
                        style={{ width: `${Math.min(100, t.current_measured_progress_pct)}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Target Details Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-2 border-t border-slate-100 text-[11px]">
                    <div>
                      <span className="text-slate-400 block">Scope</span>
                      <span className="font-semibold text-slate-800">{t.building_name || 'Campus-Wide'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Target Reduction</span>
                      <span className="font-semibold text-emerald-700">-{t.target_reduction_pct}%</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Target Date</span>
                      <span className="font-semibold text-slate-800">
                        {new Date(t.target_completion_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* TAB 5: VERIFIED SAVINGS LEDGER */}
      {activeTab === 'verification' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-5 border-b border-slate-200">
              <h2 className="text-base font-bold text-slate-900">Empirical Recommendation Savings & Verification Ledger</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Every corrective recommendation is audited by comparing post-action meter readings against baseline periods under equivalent context
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Recommendation / Directive</th>
                    <th className="py-3 px-4">Facility</th>
                    <th className="py-3 px-4 text-right">Baseline Avg</th>
                    <th className="py-3 px-4 text-right">Post-Action Avg</th>
                    <th className="py-3 px-4 text-right">Measured Reduction</th>
                    <th className="py-3 px-4 text-right">Cost Saved</th>
                    <th className="py-3 px-4 text-right">Avoided CO₂e</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {verifications.map(v => (
                    <tr key={v.id} className="hover:bg-slate-50/75 transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-slate-900 max-w-xs truncate" title={v.recommendation_title}>
                        {v.recommendation_title || `Directive #${v.recommendation_id}`}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">{v.building_name || 'Campus'}</td>
                      <td className="py-3.5 px-4 text-right font-mono text-slate-500">{v.baseline_avg_kwh} kWh</td>
                      <td className="py-3.5 px-4 text-right font-mono text-slate-900 font-semibold">{v.post_action_avg_kwh} kWh</td>
                      <td className="py-3.5 px-4 text-right font-mono font-bold text-emerald-700">
                        {v.observed_reduction_kwh > 0 ? `-${v.observed_reduction_kwh} kWh (-${v.observed_reduction_pct}%)` : '0.0 kWh'}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-semibold text-slate-900">
                        ₹{v.cost_savings_inr.toLocaleString()}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono text-emerald-800">
                        {v.emissions_reduction_kg_co2e} kg
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          v.verification_status === 'verified'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : v.verification_status === 'insufficient_data'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-slate-100 text-slate-700'
                        }`}>
                          {v.verification_status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <button
                          onClick={() => handleVerify(v.recommendation_id)}
                          disabled={verifyingId === v.recommendation_id}
                          className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200 text-[10px] font-semibold transition-colors disabled:opacity-50"
                        >
                          {verifyingId === v.recommendation_id ? 'Auditing...' : 'Re-verify'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CONFIGURE TARGET */}
      {showTargetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-900 text-base">Configure Sustainability Target</h3>
              <button onClick={() => setShowTargetModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">✕</button>
            </div>

            <form onSubmit={handleCreateTarget} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-medium mb-1">Target Initiative Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., CIT-LIB Weekend HVAC Optimization"
                  value={newTarget.name}
                  onChange={(e) => setNewTarget({ ...newTarget, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Scope Facility (Optional)</label>
                <select
                  value={newTarget.building_id || ''}
                  onChange={(e) => setNewTarget({ ...newTarget, building_id: e.target.value ? Number(e.target.value) : undefined })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Campus-Wide Scope</option>
                  {allBuildings.map(b => (
                    <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Target Reduction (%) *</label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max="100"
                    required
                    value={newTarget.target_reduction_pct}
                    onChange={(e) => setNewTarget({ ...newTarget, target_reduction_pct: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Baseline Consumption (kWh) *</label>
                  <input
                    type="number"
                    step="100"
                    min="100"
                    required
                    value={newTarget.baseline_value}
                    onChange={(e) => setNewTarget({ ...newTarget, baseline_value: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Target Completion Date *</label>
                <input
                  type="date"
                  required
                  value={newTarget.target_completion_date}
                  onChange={(e) => setNewTarget({ ...newTarget, target_completion_date: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowTargetModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-semibold shadow-xs"
                >
                  Register Target
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: SUSTAINABILITY AUDIT REPORT VIEW */}
      {showReportModal && report && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-3xl w-full p-6 space-y-6 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200">
              <div>
                <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Formal Audit Documentation</span>
                <h3 className="font-bold text-slate-900 text-lg mt-0.5">{report.report_title}</h3>
                <p className="text-xs text-slate-500">Generated: {new Date(report.generated_at).toLocaleString()}</p>
              </div>
              <button onClick={() => setShowReportModal(false)} className="text-slate-400 hover:text-slate-600 font-bold text-lg">✕</button>
            </div>

            {/* Provenance Disclaimer */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 leading-relaxed font-mono">
              {report.data_provenance_disclaimer}
            </div>

            {/* Metrics Table */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">Total Electricity</span>
                <span className="font-bold text-slate-900 text-base">{report.summary_metrics.total_energy_kwh.toLocaleString()} kWh</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">Carbon Emissions</span>
                <span className="font-bold text-emerald-800 text-base">{report.summary_metrics.total_emissions_tonnes_co2e} t CO₂e</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">Energy Intensity</span>
                <span className="font-bold text-indigo-700 text-base">{report.summary_metrics.average_energy_intensity_kwh_sqm} kWh/m²</span>
              </div>
              <div className="p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">Verified Savings</span>
                <span className="font-bold text-teal-700 text-base">₹{report.summary_metrics.verified_savings_inr.toLocaleString()}</span>
              </div>
            </div>

            {/* Methodology Principles */}
            <div>
              <h4 className="font-bold text-slate-800 text-xs mb-2">Methodology Standards & Audit Standards:</h4>
              <ul className="space-y-1 text-xs text-slate-600 list-disc list-inside">
                {report.methodology_notes.map((note, idx) => (
                  <li key={idx}>{note}</li>
                ))}
              </ul>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-slate-200">
              <button
                onClick={handleDownloadReportCSV}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                <Download className="w-3.5 h-3.5" />
                Download CSV Data
              </button>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800"
              >
                Print Official Audit Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default Sustainability
