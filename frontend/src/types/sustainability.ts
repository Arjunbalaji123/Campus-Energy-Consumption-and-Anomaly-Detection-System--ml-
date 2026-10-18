/**
 * TypeScript interfaces for Campus Sustainability Intelligence Module.
 */

export interface EmissionsFactorInfo {
  config_key: string
  emission_factor: number
  unit: string
  source_name: string
  effective_date: string
  applicable_region: string
  notes?: string
}

export interface SustainabilitySummary {
  reporting_period_start?: string
  reporting_period_end?: string
  total_energy_kwh: number
  total_emissions_kg_co2e: number
  total_emissions_tonnes_co2e: number
  average_energy_intensity_kwh_sqm: number
  total_cost_inr: number
  potential_savings_kwh: number
  potential_savings_inr: number
  verified_savings_kwh: number
  verified_savings_inr: number
  verified_emissions_reduction_kg_co2e: number
  total_recommendations_count: number
  verified_completed_count: number
  in_progress_count: number
  emissions_factor_info: EmissionsFactorInfo
  is_synthetic_notice: string
}

export interface BuildingSustainability {
  building_id: number
  name: string
  code: string
  category: string
  floor_area_sqm: number
  total_energy_kwh: number
  energy_intensity_kwh_sqm: number
  emissions_kg_co2e: number
  baseline_expected_kwh: number
  deviation_pct: number
  anomaly_count: number
  recommendations_count: number
  verified_savings_kwh: number
}

export interface SustainabilityTrendPoint {
  timestamp: string
  actual_kwh: number
  baseline_kwh: number
  emissions_kg_co2e: number
  energy_intensity_kwh_sqm: number
  is_anomaly: boolean
}

export interface SustainabilityTrends {
  building_id?: number
  building_name?: string
  granularity: 'daily' | 'hourly'
  trends: SustainabilityTrendPoint[]
}

export interface CarbonBuildingBreakdown {
  building_id: number
  name: string
  code: string
  category: string
  emissions_kg_co2e: number
  emissions_tonnes_co2e: number
  percentage_of_campus: number
  intensity_kwh_sqm: number
}

export interface CarbonFootprint {
  scope_boundary_notice: string
  emissions_factor: EmissionsFactorInfo
  total_emissions_kg_co2e: number
  total_emissions_tonnes_co2e: number
  building_breakdown: CarbonBuildingBreakdown[]
  equivalencies: {
    tree_seedlings_10_years: number
    passenger_vehicle_km_avoided: number
    indian_households_monthly_power: number
    methodology_reference: string
  }
}

export interface SustainabilityTarget {
  id: number
  name: string
  description?: string
  building_id?: number
  building_name?: string
  metric_type: string
  target_reduction_pct: number
  baseline_period_start: string
  baseline_period_end: string
  baseline_value: number
  target_completion_date: string
  current_measured_progress_pct: number
  current_measured_value?: number
  status: 'in_progress' | 'achieved' | 'at_risk' | 'expired'
  last_calculated_at: string
  created_at: string
  updated_at: string
}

export interface SustainabilityTargetCreate {
  name: string
  description?: string
  building_id?: number
  metric_type?: string
  target_reduction_pct: number
  baseline_period_start: string
  baseline_period_end: string
  baseline_value: number
  target_completion_date: string
}

export interface SustainabilityVerification {
  id: number
  recommendation_id: number
  recommendation_title?: string
  building_name?: string
  baseline_period_start: string
  baseline_period_end: string
  baseline_avg_kwh: number
  post_action_period_start: string
  post_action_period_end: string
  post_action_avg_kwh: number
  observed_reduction_kwh: number
  observed_reduction_pct: number
  cost_savings_inr: number
  emissions_reduction_kg_co2e: number
  verification_status: 'verified' | 'pending' | 'insufficient_data' | 'reverted'
  verification_criteria: string
  verified_by: string
  verified_at?: string
  notes?: string
  created_at: string
}

export interface SustainabilityReport {
  report_title: string
  generated_at: string
  reporting_period_start?: string
  reporting_period_end?: string
  data_provenance_disclaimer: string
  emissions_factor_provenance: EmissionsFactorInfo
  summary_metrics: SustainabilitySummary
  building_benchmarks: BuildingSustainability[]
  targets_status: SustainabilityTarget[]
  verified_savings_ledger: SustainabilityVerification[]
  methodology_notes: string[]
}

