/**
 * TypeScript interface definitions matching backend Pydantic schemas.
 */

export interface Building {
  id: number
  name: string
  code: string
  category: string
  floors?: number | null
  floor_area_sqm?: number | null
  max_capacity?: number | null
  operating_hours?: string | null
  operating_days?: string | null
  has_hvac: boolean
  lighting_type?: string | null
  meter_identifier?: string | null
  notes?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BuildingCreate {
  name: string
  code: string
  category: string
  floors?: number | null
  floor_area_sqm?: number | null
  max_capacity?: number | null
  operating_hours?: string | null
  operating_days?: string | null
  has_hvac: boolean
  lighting_type?: string | null
  meter_identifier?: string | null
  notes?: string | null
  is_active?: boolean
}

export interface EnergyReading {
  id: number
  building_id: number
  building_name?: string | null
  building_code?: string | null
  timestamp: string
  energy_kwh: number
  meter_interval_minutes: number
  indoor_temp_c?: number | null
  outdoor_temp_c?: number | null
  relative_humidity?: number | null
  occupancy_count?: number | null
  day_type: string
  operating_status: string
  hvac_status?: string | null
  tariff_rate?: number | null
  data_source: string
  is_synthetic: boolean
  notes?: string | null
  created_at: string
}

export interface EnergyReadingCreate {
  building_id: number
  timestamp: string
  energy_kwh: number
  meter_interval_minutes: number
  indoor_temp_c?: number | null
  outdoor_temp_c?: number | null
  relative_humidity?: number | null
  occupancy_count?: number | null
  day_type: string
  operating_status: string
  hvac_status?: string | null
  tariff_rate?: number | null
  data_source: string
  notes?: string | null
}

export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  total_pages: number
  items: T[]
}

export interface Prediction {
  id: number
  reading_id: number
  building_id: number
  building_name?: string | null
  building_code?: string | null
  timestamp?: string | null
  actual_energy_kwh?: number | null
  predicted_energy_kwh: number
  residual_kwh: number
  deviation_pct?: number | null
  model_version_tag?: string | null
  created_at: string
}

export interface AnomalyEvent {
  id: number
  reading_id: number
  prediction_id?: number | null
  building_id: number
  building_name?: string | null
  building_code?: string | null
  timestamp: string
  actual_energy_kwh: number
  predicted_energy_kwh?: number | null
  residual_kwh?: number | null
  deviation_pct?: number | null
  detection_method: string
  severity: 'normal' | 'warning' | 'critical'
  anomaly_score?: number | null
  status: 'open' | 'investigating' | 'resolved' | 'dismissed'
  detected_at: string

  // Forensic environmental & building context
  indoor_temp_c?: number | null
  outdoor_temp_c?: number | null
  relative_humidity?: number | null
  occupancy_count?: number | null
  max_capacity?: number | null
  day_type?: string | null
  operating_status?: string | null
  hvac_status?: string | null
  floor_area_sqm?: number | null

  explanations?: AnomalyExplanation[]
  recommendations?: Recommendation[]
}

export interface AnomalyExplanation {
  id: number
  anomaly_event_id: number
  primary_hypothesis: string
  evidence: Record<string, any>
  confidence: 'low' | 'medium' | 'high'
  data_to_confirm?: string | null
  recommended_next_action?: string | null
  created_at: string
}

export interface Recommendation {
  id: number
  anomaly_event_id: number
  title: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  supporting_evidence: string
  recommended_action: string
  responsible_role: string
  follow_up_verification?: string | null
  status: 'open' | 'investigating' | 'resolved' | 'dismissed'
  estimated_savings_kwh?: number | null
  building_name?: string | null
  building_code?: string | null
  created_at: string
}

export interface DashboardOverview {
  total_energy_kwh: number
  total_cost_inr: number
  total_readings: number
  total_buildings: number
  active_anomalies_count: number
  anomaly_severity_breakdown: {
    critical: number
    warning: number
    normal: number
  }
  building_consumption: {
    building_id: number
    building_name: string
    building_code: string
    building_category: string
    total_energy_kwh: number
    avg_hourly_kwh: number
    reading_count: number
    anomaly_count: number
  }[]
  recent_alerts: {
    anomaly_id: number
    reading_id: number
    building_name: string
    building_code: string
    timestamp: string
    actual_energy_kwh: number
    predicted_energy_kwh?: number | null
    residual_kwh?: number | null
    deviation_pct?: number | null
    severity: string
    detection_method: string
    status: string
  }[]
  model_status: Record<string, any>
  server_time: string
}

export interface CSVImportResult {
  total_rows: number
  imported: number
  skipped_duplicates: number
  errors: string[]
}

export interface TimeSeriesPoint {
  timestamp: string
  energy_kwh: number
  predicted_kwh?: number | null
  residual_kwh?: number | null
  is_anomaly: boolean
  severity?: string | null
}

export interface DiurnalPoint {
  hour: number
  working_day_avg: number
  weekend_avg: number
}

export interface DashboardAnalyticsResponse {
  building_id?: number | null
  building_name?: string | null
  building_code?: string | null
  timeseries: TimeSeriesPoint[]
  diurnal_profile: DiurnalPoint[]
}

