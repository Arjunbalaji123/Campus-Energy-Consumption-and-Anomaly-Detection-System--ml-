/**
 * Centralized API client service for CIT Campus Energy System backend.
 */
import type {
  Building, BuildingCreate, EnergyReading, EnergyReadingCreate,
  PaginatedResponse, Prediction, AnomalyEvent, Recommendation,
  DashboardOverview, CSVImportResult, DashboardAnalyticsResponse,
  SustainabilitySummary, BuildingSustainability, SustainabilityTrends,
  CarbonFootprint, EmissionsFactorInfo, SustainabilityTarget,
  SustainabilityTargetCreate, SustainabilityVerification, SustainabilityReport
} from '../types'

const BASE_URL = '/api'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`
    try {
      const errJson = await res.json()
      if (errJson.detail) {
        errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail)
      }
    } catch {
      errorMsg = await res.text() || errorMsg
    }
    throw new Error(errorMsg)
  }
  if (res.status === 204) {
    return {} as T
  }
  return res.json()
}

export const api = {
  // Health
  getHealth: () => fetch(`${BASE_URL}/health`).then(res => handleResponse<{ status: string; database: any }>(res)),

  // Dashboard Overview & Analytics
  getDashboardOverview: () => fetch(`${BASE_URL}/dashboard/overview`).then(res => handleResponse<DashboardOverview>(res)),
  getDashboardTimeseries: (buildingId?: number, limit = 168) => {
    let url = `${BASE_URL}/dashboard/timeseries?limit=${limit}`
    if (buildingId) url += `&building_id=${buildingId}`
    return fetch(url).then(res => handleResponse<DashboardAnalyticsResponse>(res))
  },

  // Buildings
  getBuildings: (activeOnly = true, category?: string) => {
    let url = `${BASE_URL}/buildings?active_only=${activeOnly}`
    if (category) url += `&category=${encodeURIComponent(category)}`
    return fetch(url).then(res => handleResponse<Building[]>(res))
  },
  getBuilding: (id: number) => fetch(`${BASE_URL}/buildings/${id}`).then(res => handleResponse<Building>(res)),
  createBuilding: (data: BuildingCreate) => fetch(`${BASE_URL}/buildings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(res => handleResponse<Building>(res)),
  updateBuilding: (id: number, data: Partial<BuildingCreate>) => fetch(`${BASE_URL}/buildings/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(res => handleResponse<Building>(res)),
  deactivateBuilding: (id: number) => fetch(`${BASE_URL}/buildings/${id}`, { method: 'DELETE' }).then(res => handleResponse<Building>(res)),

  // Energy Readings
  getReadings: (page = 1, pageSize = 20, buildingId?: number, dayType?: string) => {
    let url = `${BASE_URL}/readings?page=${page}&page_size=${pageSize}`
    if (buildingId) url += `&building_id=${buildingId}`
    if (dayType) url += `&day_type=${encodeURIComponent(dayType)}`
    return fetch(url).then(res => handleResponse<PaginatedResponse<EnergyReading>>(res))
  },
  submitReading: (data: EnergyReadingCreate) => fetch(`${BASE_URL}/readings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(res => handleResponse<EnergyReading>(res)),
  deleteReading: (id: number) => fetch(`${BASE_URL}/readings/${id}`, { method: 'DELETE' }).then(res => handleResponse<void>(res)),

  // CSV I/O
  importCSV: async (file: File): Promise<CSVImportResult> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${BASE_URL}/readings/import/csv`, {
      method: 'POST',
      body: formData,
    })
    return handleResponse<CSVImportResult>(res)
  },
  getExportCSVUrl: (buildingId?: number) => {
    let url = `${BASE_URL}/readings/export/csv`
    if (buildingId) url += `?building_id=${buildingId}`
    return url
  },

  // Predictions
  generatePrediction: (readingId: number) => fetch(`${BASE_URL}/predictions/generate/${readingId}`, {
    method: 'POST',
  }).then(res => handleResponse<Prediction>(res)),
  getPredictions: (page = 1, pageSize = 20, buildingId?: number) => {
    let url = `${BASE_URL}/predictions?page=${page}&page_size=${pageSize}`
    if (buildingId) url += `&building_id=${buildingId}`
    return fetch(url).then(res => handleResponse<PaginatedResponse<Prediction>>(res))
  },

  // Anomalies
  detectAnomaly: (readingId: number) => fetch(`${BASE_URL}/anomalies/detect/${readingId}`, {
    method: 'POST',
  }).then(res => handleResponse<AnomalyEvent | null>(res)),
  getAnomaly: (id: number) => fetch(`${BASE_URL}/anomalies/${id}`).then(res => handleResponse<AnomalyEvent>(res)),
  getAnomalies: (page = 1, pageSize = 20, severity?: string, status?: string) => {
    let url = `${BASE_URL}/anomalies?page=${page}&page_size=${pageSize}`
    if (severity) url += `&severity=${severity}`
    if (status) url += `&status=${status}`
    return fetch(url).then(res => handleResponse<PaginatedResponse<AnomalyEvent>>(res))
  },
  updateAnomalyStatus: (id: number, status: string) => fetch(`${BASE_URL}/anomalies/${id}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  }).then(res => handleResponse<AnomalyEvent>(res)),
  runBatchScan: (limit = 2000) => fetch(`${BASE_URL}/anomalies/batch-scan?limit=${limit}`, {
    method: 'POST',
  }).then(res => handleResponse<any>(res)),

  // Recommendations
  getRecommendations: (page = 1, pageSize = 20, priority?: string, status?: string) => {
    let url = `${BASE_URL}/recommendations?page=${page}&page_size=${pageSize}`
    if (priority) url += `&priority=${priority}`
    if (status) url += `&status=${status}`
    return fetch(url).then(res => handleResponse<PaginatedResponse<Recommendation>>(res))
  },
  updateRecommendationStatus: (id: number, status: string) => fetch(`${BASE_URL}/recommendations/${id}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  }).then(res => handleResponse<Recommendation>(res)),

  // Settings
  getSettings: () => fetch(`${BASE_URL}/settings`).then(res => handleResponse<any>(res)),
  updateThresholds: (warning: number, critical: number) => fetch(`${BASE_URL}/settings/thresholds`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ warning_threshold: warning, critical_threshold: critical }),
  }).then(res => handleResponse<any>(res)),

  // Model Comparison
  getModelComparison: () => fetch(`${BASE_URL}/models/comparison`).then(res => handleResponse<any>(res)),

  // Sustainability Module
  getSustainabilitySummary: (startDate?: string, endDate?: string, buildingId?: number) => {
    let url = `${BASE_URL}/sustainability/summary?`
    if (startDate) url += `start_date=${encodeURIComponent(startDate)}&`
    if (endDate) url += `end_date=${encodeURIComponent(endDate)}&`
    if (buildingId) url += `building_id=${buildingId}&`
    return fetch(url).then(res => handleResponse<SustainabilitySummary>(res))
  },

  getBuildingSustainability: (startDate?: string, endDate?: string) => {
    let url = `${BASE_URL}/sustainability/buildings?`
    if (startDate) url += `start_date=${encodeURIComponent(startDate)}&`
    if (endDate) url += `end_date=${encodeURIComponent(endDate)}&`
    return fetch(url).then(res => handleResponse<BuildingSustainability[]>(res))
  },

  getSustainabilityTrends: (buildingId?: number, startDate?: string, endDate?: string, granularity: 'daily' | 'hourly' = 'daily') => {
    let url = `${BASE_URL}/sustainability/trends?granularity=${granularity}&`
    if (buildingId) url += `building_id=${buildingId}&`
    if (startDate) url += `start_date=${encodeURIComponent(startDate)}&`
    if (endDate) url += `end_date=${encodeURIComponent(endDate)}&`
    return fetch(url).then(res => handleResponse<SustainabilityTrends>(res))
  },

  getCarbonFootprint: (startDate?: string, endDate?: string) => {
    let url = `${BASE_URL}/sustainability/emissions?`
    if (startDate) url += `start_date=${encodeURIComponent(startDate)}&`
    if (endDate) url += `end_date=${encodeURIComponent(endDate)}&`
    return fetch(url).then(res => handleResponse<CarbonFootprint>(res))
  },

  getGridEmissionFactor: () => fetch(`${BASE_URL}/sustainability/factor`).then(res => handleResponse<EmissionsFactorInfo>(res)),

  updateGridEmissionFactor: (data: Partial<EmissionsFactorInfo>) => fetch(`${BASE_URL}/sustainability/factor`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(res => handleResponse<EmissionsFactorInfo>(res)),

  getSustainabilityTargets: () => fetch(`${BASE_URL}/sustainability/targets`).then(res => handleResponse<SustainabilityTarget[]>(res)),

  createSustainabilityTarget: (data: SustainabilityTargetCreate) => fetch(`${BASE_URL}/sustainability/targets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(res => handleResponse<SustainabilityTarget>(res)),

  getSustainabilityVerifications: () => fetch(`${BASE_URL}/sustainability/verification`).then(res => handleResponse<SustainabilityVerification[]>(res)),

  verifyRecommendationImpact: (recommendationId: number, data?: any) => fetch(`${BASE_URL}/sustainability/verify/${recommendationId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  }).then(res => handleResponse<SustainabilityVerification>(res)),

  getSustainabilityReport: (startDate?: string, endDate?: string) => {
    let url = `${BASE_URL}/sustainability/report?`
    if (startDate) url += `start_date=${encodeURIComponent(startDate)}&`
    if (endDate) url += `end_date=${encodeURIComponent(endDate)}&`
    return fetch(url).then(res => handleResponse<SustainabilityReport>(res))
  },
}
