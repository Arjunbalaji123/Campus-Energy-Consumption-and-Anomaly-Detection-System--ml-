import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import type { Building, BuildingCreate } from '../types'

const BUILDING_CATEGORIES = [
  'Academic Block',
  'Laboratory Block',
  'Administrative Block',
  'Library',
  'IT Block',
  'Workshop / Equipment Block',
  'Other Campus Buildings',
]

export const Buildings: React.FC = () => {
  const [buildings, setBuildings] = useState<Building[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')
  const [showActiveOnly, setShowActiveOnly] = useState<boolean>(false)

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingBuilding, setEditingBuilding] = useState<Building | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Form State
  const [formData, setFormData] = useState<BuildingCreate>({
    name: '',
    code: '',
    category: 'Academic Block',
    floors: null,
    floor_area_sqm: null,
    max_capacity: null,
    operating_hours: '08:30 - 17:30',
    operating_days: 'Monday - Saturday',
    has_hvac: false,
    lighting_type: 'LED fixtures',
    meter_identifier: '',
    notes: '',
    is_active: true,
  })

  const fetchBuildings = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getBuildings(showActiveOnly)
      setBuildings(data)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch buildings registry.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBuildings()
  }, [showActiveOnly])

  const openCreateModal = () => {
    setEditingBuilding(null)
    setFormData({
      name: '',
      code: '',
      category: 'Academic Block',
      floors: null,
      floor_area_sqm: null,
      max_capacity: null,
      operating_hours: '08:30 - 17:30',
      operating_days: 'Monday - Saturday',
      has_hvac: false,
      lighting_type: 'LED fixtures',
      meter_identifier: '',
      notes: '',
      is_active: true,
    })
    setIsModalOpen(true)
  }

  const openEditModal = (b: Building) => {
    setEditingBuilding(b)
    setFormData({
      name: b.name,
      code: b.code,
      category: b.category,
      floors: b.floors ?? null,
      floor_area_sqm: b.floor_area_sqm ?? null,
      max_capacity: b.max_capacity ?? null,
      operating_hours: b.operating_hours || '',
      operating_days: b.operating_days || '',
      has_hvac: b.has_hvac,
      lighting_type: b.lighting_type || '',
      meter_identifier: b.meter_identifier || '',
      notes: b.notes || '',
      is_active: b.is_active,
    })
    setIsModalOpen(true)
  }

  const handleToggleDeactivate = async (b: Building) => {
    const action = b.is_active ? 'deactivate' : 'activate'
    if (!window.confirm(`Are you sure you want to ${action} ${b.name} (${b.code})?`)) return

    try {
      if (b.is_active) {
        await api.deactivateBuilding(b.id)
      } else {
        await api.updateBuilding(b.id, { is_active: true })
      }
      setSuccessMsg(`Successfully updated status of ${b.code}.`)
      fetchBuildings()
      setTimeout(() => setSuccessMsg(null), 4000)
    } catch (err: any) {
      setError(err.message || `Failed to update status for ${b.code}`)
    }
  }

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      if (editingBuilding) {
        await api.updateBuilding(editingBuilding.id, formData)
        setSuccessMsg(`Building ${formData.name} updated successfully.`)
      } else {
        await api.createBuilding(formData)
        setSuccessMsg(`New building ${formData.name} registered successfully.`)
      }
      setIsModalOpen(false)
      fetchBuildings()
      setTimeout(() => setSuccessMsg(null), 4000)
    } catch (err: any) {
      setError(err.message || 'Operation failed. Please review the inputs.')
    } finally {
      setSubmitting(false)
    }
  }

  // Filtered buildings
  const filteredBuildings = buildings.filter((b) => {
    const matchesCategory = selectedCategory === 'ALL' || b.category === selectedCategory
    const matchesSearch =
      b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (b.meter_identifier && b.meter_identifier.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesCategory && matchesSearch
  })

  const totalArea = buildings.reduce((acc, b) => acc + (b.floor_area_sqm || 0), 0)
  const hvacCount = buildings.filter((b) => b.has_hvac).length
  const activeCount = buildings.filter((b) => b.is_active).length

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
              CIT Campus Registry
            </span>
            <span className="text-xs text-slate-400 font-mono">Normalized DB Entity #1</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mt-1">Campus Buildings Registry</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage Coimbatore Institute of Technology facilities, physical characteristics, HVAC availability, and sub-meter identifiers.
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm transition-colors shadow-sm self-start md:self-auto"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          Register Building
        </button>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-emerald-600 font-bold">✓</span>
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-600 hover:text-emerald-900 font-bold text-sm">✕</button>
        </div>
      )}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-rose-600 font-bold">⚠</span>
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-600 hover:text-rose-900 font-bold text-sm">✕</button>
        </div>
      )}

      {/* KPI Stats Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Buildings</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{buildings.length}</div>
          <span className="text-xs text-slate-400">Campus facilities catalogued</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active Monitoring</span>
          <div className="text-2xl font-bold text-emerald-600 mt-1">{activeCount}</div>
          <span className="text-xs text-slate-400">{buildings.length - activeCount} deactivated</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">HVAC Equipped</span>
          <div className="text-2xl font-bold text-indigo-600 mt-1">{hvacCount}</div>
          <span className="text-xs text-slate-400">{((hvacCount / (buildings.length || 1)) * 100).toFixed(0)}% of campus blocks</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Floor Area</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{totalArea.toLocaleString()} <span className="text-sm font-normal text-slate-500">m²</span></div>
          <span className="text-xs text-slate-400">Energy intensity denominator</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
        <div className="flex-1 flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Search by building name, code, or meter ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            <svg className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
          >
            <option value="ALL">All Categories</option>
            {BUILDING_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={showActiveOnly}
              onChange={(e) => setShowActiveOnly(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4"
            />
            <span>Active only</span>
          </label>

          <button
            onClick={fetchBuildings}
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            title="Refresh buildings list"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Buildings Cards Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-2"></div>
          <p className="text-sm">Loading CIT campus building registry...</p>
        </div>
      ) : filteredBuildings.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
          <p className="text-base font-medium">No buildings found matching your filters.</p>
          <p className="text-xs text-slate-400 mt-1">Try resetting filters or click "Register Building" to add a new campus facility.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBuildings.map((building) => (
            <div
              key={building.id}
              className={`bg-white rounded-xl border ${
                building.is_active ? 'border-slate-200' : 'border-slate-300 opacity-75'
              } shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between overflow-hidden`}
            >
              <div className="p-5 space-y-4">
                {/* Card Header */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-100 text-slate-700">
                      {building.code}
                    </span>
                    <h3 className="text-lg font-bold text-slate-800 mt-1">{building.name}</h3>
                    <span className="inline-block text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded mt-1">
                      {building.category}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                      building.is_active
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {building.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                {/* Key Specifications Grid */}
                <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-slate-100 text-slate-600">
                  <div>
                    <span className="text-slate-400">Floors:</span>{' '}
                    <span className="font-semibold text-slate-700">{building.floors ?? 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Floor Area:</span>{' '}
                    <span className="font-semibold text-slate-700">
                      {building.floor_area_sqm ? `${building.floor_area_sqm.toLocaleString()} m²` : 'Unknown'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Max Capacity:</span>{' '}
                    <span className="font-semibold text-slate-700">
                      {building.max_capacity ? `${building.max_capacity} people` : 'Unknown'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">HVAC Status:</span>{' '}
                    <span className={`font-semibold ${building.has_hvac ? 'text-indigo-600' : 'text-slate-500'}`}>
                      {building.has_hvac ? 'Equipped' : 'Natural/Fans'}
                    </span>
                  </div>
                </div>

                {/* Operating Info */}
                <div className="space-y-1 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Hours:</span>
                    <span className="font-medium text-slate-700">{building.operating_hours || 'Standard'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Days:</span>
                    <span className="font-medium text-slate-700">{building.operating_days || 'Standard'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Meter ID:</span>
                    <span className="font-mono text-indigo-700">{building.meter_identifier || 'Unassigned'}</span>
                  </div>
                </div>

                {/* Notes / Data Quality */}
                {building.notes && (
                  <div className="text-xs bg-slate-50 p-2.5 rounded border border-slate-100 text-slate-500 line-clamp-2">
                    <span className="font-medium text-slate-600">Note:</span> {building.notes}
                  </div>
                )}
              </div>

              {/* Card Footer Actions */}
              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs">
                <button
                  onClick={() => openEditModal(building)}
                  className="text-indigo-600 hover:text-indigo-900 font-medium transition-colors"
                >
                  Edit Specifications
                </button>
                <button
                  onClick={() => handleToggleDeactivate(building)}
                  className={`${
                    building.is_active ? 'text-rose-600 hover:text-rose-800' : 'text-emerald-600 hover:text-emerald-800'
                  } font-medium transition-colors`}
                >
                  {building.is_active ? 'Deactivate' : 'Reactivate'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Register / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full p-6 space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h2 className="text-lg font-bold text-slate-800">
                {editingBuilding ? `Edit Specifications: ${editingBuilding.code}` : 'Register New CIT Campus Building'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Building Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Mechanical Sciences Block"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Building Code <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    placeholder="e.g. CIT-MECH"
                    className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none uppercase"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Building Category <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white text-slate-700"
                  >
                    {BUILDING_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Meter Identifier
                  </label>
                  <input
                    type="text"
                    value={formData.meter_identifier || ''}
                    onChange={(e) => setFormData({ ...formData, meter_identifier: e.target.value })}
                    placeholder="e.g. CIT-MTR-07"
                    className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Number of Floors
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={formData.floors ?? ''}
                    onChange={(e) => setFormData({ ...formData, floors: e.target.value ? parseInt(e.target.value) : null })}
                    placeholder="e.g. 4"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Floor Area (m²)
                  </label>
                  <input
                    type="number"
                    min="10"
                    step="0.1"
                    value={formData.floor_area_sqm ?? ''}
                    onChange={(e) => setFormData({ ...formData, floor_area_sqm: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="e.g. 3200"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Maximum Occupancy Capacity
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.max_capacity ?? ''}
                    onChange={(e) => setFormData({ ...formData, max_capacity: e.target.value ? parseInt(e.target.value) : null })}
                    placeholder="e.g. 450"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Operating Hours
                  </label>
                  <input
                    type="text"
                    value={formData.operating_hours || ''}
                    onChange={(e) => setFormData({ ...formData, operating_hours: e.target.value })}
                    placeholder="e.g. 08:30 - 17:30"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Operating Days
                  </label>
                  <input
                    type="text"
                    value={formData.operating_days || ''}
                    onChange={(e) => setFormData({ ...formData, operating_days: e.target.value })}
                    placeholder="e.g. Monday - Saturday"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Lighting System
                  </label>
                  <input
                    type="text"
                    value={formData.lighting_type || ''}
                    onChange={(e) => setFormData({ ...formData, lighting_type: e.target.value })}
                    placeholder="e.g. T5 Fluorescent & LED downlights"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* HVAC Checkbox */}
              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="hvac_toggle"
                  checked={formData.has_hvac}
                  onChange={(e) => setFormData({ ...formData, has_hvac: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                />
                <label htmlFor="hvac_toggle" className="text-sm font-medium text-slate-700 cursor-pointer">
                  Equipped with Central or Split HVAC Air Conditioning
                </label>
              </div>

              {/* Notes / Data Quality */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Notes & Data Quality Context
                </label>
                <textarea
                  rows={2}
                  value={formData.notes || ''}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Document data quality status, approximate vs measured area, equipment notes..."
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              {/* Form Actions */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : editingBuilding ? 'Update Building' : 'Register Building'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
