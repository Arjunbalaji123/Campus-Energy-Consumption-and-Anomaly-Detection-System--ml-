import React, { useState, useEffect } from 'react'
import {
  Zap, PlusCircle, Search, Download, Upload, AlertCircle,
  CheckCircle2, Trash2, RefreshCw, ChevronLeft, ChevronRight
} from 'lucide-react'
import { api } from '../services/api'
import type { Building, EnergyReading, EnergyReadingCreate, Prediction, AnomalyEvent, CSVImportResult } from '../types'

export default function EnergyData() {
  const [activeTab, setActiveTab] = useState<'form' | 'table'>('form')

  // Building registry state
  const [buildings, setBuildings] = useState<Building[]>([])
  const [loadingBuildings, setLoadingBuildings] = useState(true)

  // Form state
  const [formData, setFormData] = useState<EnergyReadingCreate>({
    building_id: 1,
    timestamp: new Date().toISOString().slice(0, 16),
    energy_kwh: 50.0,
    meter_interval_minutes: 60,
    indoor_temp_c: 24.0,
    outdoor_temp_c: 30.0,
    relative_humidity: 60.0,
    occupancy_count: 100,
    day_type: 'working_day',
    operating_status: 'normal',
    hvac_status: 'on',
    tariff_rate: 7.50,
    data_source: 'manual',
    notes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [formSuccess, setFormSuccess] = useState<{
    reading: EnergyReading
    prediction?: Prediction
    anomaly?: AnomalyEvent | null
  } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  // Table state
  const [readings, setReadings] = useState<EnergyReading[]>([])
  const [totalReadings, setTotalReadings] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [filterBuilding, setFilterBuilding] = useState<number | undefined>(undefined)
  const [filterDayType, setFilterDayType] = useState<string>('')
  const [loadingTable, setLoadingTable] = useState(false)

  // CSV Import State
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<CSVImportResult | null>(null)

  // Load buildings on mount
  useEffect(() => {
    api.getBuildings()
      .then((data) => {
        setBuildings(data)
        if (data.length > 0) {
          setFormData((prev) => ({ ...prev, building_id: data[0].id }))
        }
        setLoadingBuildings(false)
      })
      .catch((err) => {
        setFormError('Failed to load campus building registry: ' + err.message)
        setLoadingBuildings(false)
      })
  }, [])

  // Load readings for table
  const loadReadings = (page: number) => {
    setLoadingTable(true)
    api.getReadings(page, 15, filterBuilding, filterDayType || undefined)
      .then((res) => {
        setReadings(res.items)
        setTotalReadings(res.total)
        setCurrentPage(res.page)
        setTotalPages(res.total_pages)
        setLoadingTable(false)
      })
      .catch((err) => {
        console.error('Error fetching readings:', err)
        setLoadingTable(false)
      })
  }

  useEffect(() => {
    if (activeTab === 'table') {
      loadReadings(currentPage)
    }
  }, [activeTab, currentPage, filterBuilding, filterDayType])

  // Form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setFormSuccess(null)
    setFormError(null)

    try {
      // 1. Submit manual reading
      const savedReading = await api.submitReading({
        ...formData,
        building_id: Number(formData.building_id),
        energy_kwh: Number(formData.energy_kwh),
        meter_interval_minutes: Number(formData.meter_interval_minutes),
        outdoor_temp_c: formData.outdoor_temp_c ? Number(formData.outdoor_temp_c) : undefined,
        indoor_temp_c: formData.indoor_temp_c ? Number(formData.indoor_temp_c) : undefined,
        relative_humidity: formData.relative_humidity ? Number(formData.relative_humidity) : undefined,
        occupancy_count: formData.occupancy_count ? Number(formData.occupancy_count) : undefined,
        tariff_rate: formData.tariff_rate ? Number(formData.tariff_rate) : undefined,
      })

      // 2. Automatically generate ML prediction
      let pred: Prediction | undefined
      try {
        pred = await api.generatePrediction(savedReading.id)
      } catch (pErr) {
        console.warn('Prediction generation warning:', pErr)
      }

      // 3. Automatically evaluate anomaly detection
      let anomaly: AnomalyEvent | null = null
      try {
        anomaly = await api.detectAnomaly(savedReading.id)
      } catch (aErr) {
        console.warn('Anomaly detection warning:', aErr)
      }

      setFormSuccess({
        reading: savedReading,
        prediction: pred,
        anomaly: anomaly,
      })
      setSubmitting(false)
    } catch (err: any) {
      setFormError(err.message || 'Submission failed.')
      setSubmitting(false)
    }
  }

  // Delete reading
  const handleDelete = async (id: number) => {
    if (!window.confirm(`Are you sure you want to delete energy observation #${id}?`)) {
      return
    }
    try {
      await api.deleteReading(id)
      loadReadings(currentPage)
    } catch (err: any) {
      alert('Delete failed: ' + err.message)
    }
  }

  // Handle CSV file upload
  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    setImportResult(null)
    try {
      const result = await api.importCSV(file)
      setImportResult(result)
      setImporting(false)
      loadReadings(1)
    } catch (err: any) {
      alert('CSV import failed: ' + err.message)
      setImporting(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Title */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Zap className="w-6 h-6 text-indigo-600" /> Campus Energy Observations
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manual observation ingestion, contextual parameter logging, and historical record explorer.
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-xs">
          <button
            onClick={() => setActiveTab('form')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'form'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" /> Manual Entry Form
          </button>
          <button
            onClick={() => setActiveTab('table')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'table'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Search className="w-3.5 h-3.5" /> Searchable Records ({totalReadings || '6,480+'})
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* TAB 1: MANUAL ENTRY FORM                                            */}
      {/* =================================================================== */}
      {activeTab === 'form' && (
        <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 md:p-8">
          <div className="border-b border-slate-100 pb-4 mb-6">
            <h2 className="text-base font-semibold text-slate-800">Submit New Energy Observation</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Enter building meter consumption and observed campus environmental context. Unknown fields may remain empty.
            </p>
          </div>

          {/* Success Banner */}
          {formSuccess && (
            <div className="mb-6 p-4 rounded-lg bg-emerald-50 border border-emerald-200">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                <div className="w-full">
                  <h3 className="text-sm font-bold text-emerald-900">Observation Recorded Successfully (ID #{formSuccess.reading.id})</h3>
                  <p className="text-xs text-emerald-700 mt-0.5">
                    Saved {formSuccess.reading.energy_kwh} kWh at {formSuccess.reading.timestamp} with data source <code>{formSuccess.reading.data_source}</code>.
                  </p>

                  {/* Immediate ML Prediction & Anomaly Feedback */}
                  {formSuccess.prediction && (
                    <div className="mt-3 p-3 bg-white rounded-md border border-emerald-100 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      <div>
                        <span className="text-slate-400 font-medium">Actual</span>
                        <p className="font-bold text-slate-800 text-sm">{formSuccess.reading.energy_kwh} kWh</p>
                      </div>
                      <div>
                        <span className="text-slate-400 font-medium">Expected (RF)</span>
                        <p className="font-bold text-indigo-600 text-sm">{formSuccess.prediction.predicted_energy_kwh} kWh</p>
                      </div>
                      <div>
                        <span className="text-slate-400 font-medium">Residual</span>
                        <p className="font-bold text-slate-700 text-sm">{formSuccess.prediction.residual_kwh > 0 ? `+${formSuccess.prediction.residual_kwh}` : formSuccess.prediction.residual_kwh} kWh</p>
                      </div>
                      <div>
                        <span className="text-slate-400 font-medium">Deviation</span>
                        <p className="font-bold text-slate-700 text-sm">
                          {formSuccess.prediction.deviation_pct != null ? `${formSuccess.prediction.deviation_pct > 0 ? `+${formSuccess.prediction.deviation_pct}` : formSuccess.prediction.deviation_pct}%` : 'N/A'}
                        </p>
                      </div>
                    </div>
                  )}

                  {formSuccess.anomaly && (
                    <div className="mt-2 text-xs font-semibold flex items-center gap-2">
                      <span className="text-slate-600">Anomaly Detection Verdict:</span>
                      <span className={`px-2 py-0.5 rounded-full uppercase font-bold text-[10px] ${
                        formSuccess.anomaly.severity === 'critical' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {formSuccess.anomaly.severity} ({formSuccess.anomaly.detection_method})
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Duplicate / Validation Error Alert */}
          {formError && (
            <div className="mb-6 p-4 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-rose-900">Submission Error</h3>
                <p className="text-xs text-rose-700 mt-1">{formError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Primary Required Fields */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 block mb-3">1. Primary Meter Details (Required)</span>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Building */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Campus Building *</label>
                  <select
                    value={formData.building_id}
                    onChange={(e) => setFormData({ ...formData, building_id: Number(e.target.value) })}
                    disabled={loadingBuildings}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  >
                    {buildings.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name} ({b.code})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Observation Date & Time */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Timestamp *</label>
                  <input
                    type="datetime-local"
                    value={formData.timestamp}
                    onChange={(e) => setFormData({ ...formData, timestamp: e.target.value })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                {/* Energy Consumption kWh */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Energy Consumed (kWh) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.energy_kwh}
                    onChange={(e) => setFormData({ ...formData, energy_kwh: Number(e.target.value) })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 font-mono"
                    required
                  />
                </div>

                {/* Meter Interval */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Meter Interval (Minutes) *</label>
                  <input
                    type="number"
                    min="1"
                    max="1440"
                    value={formData.meter_interval_minutes}
                    onChange={(e) => setFormData({ ...formData, meter_interval_minutes: Number(e.target.value) })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>
              </div>
            </div>

            {/* Context & Ambient Variables */}
            <div className="pt-2 border-t border-slate-100">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-3">2. Environmental & Auxiliary Context</span>
              <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Outdoor Temperature (°C)</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="e.g. 31.5"
                    value={formData.outdoor_temp_c ?? ''}
                    onChange={(e) => setFormData({ ...formData, outdoor_temp_c: e.target.value ? Number(e.target.value) : undefined })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Indoor Temperature (°C)</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="e.g. 24.0"
                    value={formData.indoor_temp_c ?? ''}
                    onChange={(e) => setFormData({ ...formData, indoor_temp_c: e.target.value ? Number(e.target.value) : undefined })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Relative Humidity (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    placeholder="e.g. 65"
                    value={formData.relative_humidity ?? ''}
                    onChange={(e) => setFormData({ ...formData, relative_humidity: e.target.value ? Number(e.target.value) : undefined })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Occupancy Headcount</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 150"
                    value={formData.occupancy_count ?? ''}
                    onChange={(e) => setFormData({ ...formData, occupancy_count: e.target.value ? Number(e.target.value) : undefined })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Operational State & Financial */}
            <div className="pt-2 border-t border-slate-100">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-3">3. Operational Status & Financials</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Day Type</label>
                  <select
                    value={formData.day_type}
                    onChange={(e) => setFormData({ ...formData, day_type: e.target.value })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="working_day">Working Day (Academic)</option>
                    <option value="weekend">Weekend</option>
                    <option value="holiday">Official Holiday</option>
                    <option value="special_event">Special Event / Symposium</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Operating Status</label>
                  <select
                    value={formData.operating_status}
                    onChange={(e) => setFormData({ ...formData, operating_status: e.target.value })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="normal">Normal Operations</option>
                    <option value="reduced">Reduced Operations</option>
                    <option value="closed">Closed / Standby</option>
                    <option value="exam">Examination Session</option>
                    <option value="maintenance">Maintenance</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">HVAC Runtime Status</label>
                  <select
                    value={formData.hvac_status ?? 'unknown'}
                    onChange={(e) => setFormData({ ...formData, hvac_status: e.target.value })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="on">Active (ON)</option>
                    <option value="off">Inactive (OFF)</option>
                    <option value="partial">Partial / Split Units Only</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Tariff Rate (₹/kWh)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={formData.tariff_rate ?? 7.50}
                    onChange={(e) => setFormData({ ...formData, tariff_rate: Number(e.target.value) })}
                    className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Notes */}
              <div className="mt-4">
                <label className="block text-xs font-medium text-slate-600 mb-1">Observation Notes / Audit Remarks</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Conducted evening workshop; lab PCs running for simulation test..."
                  value={formData.notes ?? ''}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                ></textarea>
              </div>
            </div>

            {/* Submit Action */}
            <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setFormData({
                  building_id: buildings[0]?.id || 1,
                  timestamp: new Date().toISOString().slice(0, 16),
                  energy_kwh: 50.0,
                  meter_interval_minutes: 60,
                  day_type: 'working_day',
                  operating_status: 'normal',
                  hvac_status: 'on',
                  tariff_rate: 7.50,
                  data_source: 'manual',
                  notes: '',
                })}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
              >
                Reset Defaults
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {submitting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Saving & Analyzing...
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5" /> Submit & Run Dual Detection
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 2: SEARCHABLE RECORDS TABLE                                     */}
      {/* =================================================================== */}
      {activeTab === 'table' && (
        <div className="bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
          {/* Controls Bar */}
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              {/* Filter by Building */}
              <select
                value={filterBuilding ?? ''}
                onChange={(e) => {
                  setFilterBuilding(e.target.value ? Number(e.target.value) : undefined)
                  setCurrentPage(1)
                }}
                className="text-xs rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-slate-700 focus:outline-hidden"
              >
                <option value="">All CIT Buildings</option>
                {buildings.map((b) => (
                  <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                ))}
              </select>

              {/* Filter by Day Type */}
              <select
                value={filterDayType}
                onChange={(e) => {
                  setFilterDayType(e.target.value)
                  setCurrentPage(1)
                }}
                className="text-xs rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-slate-700 focus:outline-hidden"
              >
                <option value="">All Day Types</option>
                <option value="working_day">Working Day</option>
                <option value="weekend">Weekend</option>
                <option value="holiday">Holiday</option>
              </select>

              <button
                onClick={() => loadReadings(currentPage)}
                disabled={loadingTable}
                className="px-2.5 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-100 flex items-center gap-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingTable ? 'animate-spin' : ''}`} /> Refresh
              </button>
            </div>

            {/* CSV Actions */}
            <div className="flex items-center gap-2">
              <a
                href={api.getExportCSVUrl(filterBuilding)}
                download
                className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 flex items-center gap-1.5 shadow-2xs"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" /> Export CSV
              </a>

              <label className="px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 cursor-pointer flex items-center gap-1.5 shadow-2xs">
                <Upload className="w-3.5 h-3.5 text-indigo-600" />
                <span>{importing ? 'Importing...' : 'Upload CSV'}</span>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleCSVUpload}
                  disabled={importing}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Import Result Notification */}
          {importResult && (
            <div className="p-3 bg-indigo-50 border-b border-indigo-100 text-xs text-indigo-900 flex items-center justify-between">
              <span>
                CSV Upload Complete: Processed {importResult.total_rows} rows | Imported {importResult.imported} | Skipped {importResult.skipped_duplicates} duplicates.
              </span>
              <button onClick={() => setImportResult(null)} className="text-indigo-600 hover:underline">Dismiss</button>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/75 border-b border-slate-200 text-slate-600 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Building</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 font-mono">Energy (kWh)</th>
                  <th className="py-3 px-4">Context (Temp / Occ)</th>
                  <th className="py-3 px-4">Day Type</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Source</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {readings.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-4 font-mono text-slate-500">#{r.id}</td>
                    <td className="py-2.5 px-4 font-semibold text-slate-800">
                      <div>{r.building_name}</div>
                      <span className="text-[10px] text-slate-400 font-mono">{r.building_code}</span>
                    </td>
                    <td className="py-2.5 px-4 text-slate-600 whitespace-nowrap">
                      {new Date(r.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-2.5 px-4 font-mono font-bold text-slate-900">
                      {r.energy_kwh.toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-slate-600">
                      {r.outdoor_temp_c !== null ? `${r.outdoor_temp_c}°C` : '—'} / {r.occupancy_count !== null ? `${r.occupancy_count} people` : '—'}
                    </td>
                    <td className="py-2.5 px-4">
                      <span className="capitalize text-slate-700">{r.day_type.replace('_', ' ')}</span>
                    </td>
                    <td className="py-2.5 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        r.operating_status === 'normal' ? 'bg-slate-100 text-slate-700' : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {r.operating_status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        r.data_source === 'manual' ? 'bg-indigo-50 text-indigo-700 border border-indigo-200 font-semibold' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {r.data_source}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <button
                        onClick={() => handleDelete(r.id)}
                        title="Delete Observation"
                        className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}

                {readings.length === 0 && !loadingTable && (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-400 text-xs">
                      No energy records found matching filter criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Bar */}
          <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-600">
            <div>
              Showing page <span className="font-semibold text-slate-900">{currentPage}</span> of <span className="font-semibold text-slate-900">{totalPages}</span> ({totalReadings} total records)
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1 || loadingTable}
                className="px-2.5 py-1 text-xs border border-slate-300 rounded-md bg-white hover:bg-slate-100 disabled:opacity-40 flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Prev
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages || loadingTable}
                className="px-2.5 py-1 text-xs border border-slate-300 rounded-md bg-white hover:bg-slate-100 disabled:opacity-40 flex items-center gap-1"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
