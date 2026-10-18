"""Pydantic schemas for Sustainability Intelligence Module.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class EmissionsFactorInfo(BaseModel):
    """Provenance and specification of the regional grid emission factor."""
    config_key: str = "grid_emission_factor"
    emission_factor: float = Field(..., description="kg CO2e per kWh")
    unit: str = "kg CO2e/kWh"
    source_name: str = "Central Electricity Authority (CEA) of India, CO2 Baseline Database v19"
    effective_date: str = "2024-2025"
    applicable_region: str = "Southern Regional Grid (Tamil Nadu / Coimbatore)"
    notes: Optional[str] = None


class EmissionsFactorUpdate(BaseModel):
    """Schema for updating emission factor settings."""
    emission_factor: float = Field(..., gt=0.0, description="New emission factor in kg CO2e/kWh")
    source_name: Optional[str] = None
    effective_date: Optional[str] = None
    applicable_region: Optional[str] = None
    notes: Optional[str] = None


class SustainabilitySummaryResponse(BaseModel):
    """High-level campus sustainability KPIs."""
    reporting_period_start: Optional[datetime] = None
    reporting_period_end: Optional[datetime] = None
    total_energy_kwh: float
    total_emissions_kg_co2e: float
    total_emissions_tonnes_co2e: float
    average_energy_intensity_kwh_sqm: float
    total_cost_inr: float
    potential_savings_kwh: float
    potential_savings_inr: float
    verified_savings_kwh: float
    verified_savings_inr: float
    verified_emissions_reduction_kg_co2e: float
    total_recommendations_count: int
    verified_completed_count: int
    in_progress_count: int
    emissions_factor_info: EmissionsFactorInfo
    is_synthetic_notice: str = "Simulated campus baseline dataset for educational/research evaluation"


class BuildingSustainabilityItem(BaseModel):
    """Building-level sustainability benchmark row."""
    building_id: int
    name: str
    code: str
    category: str
    floor_area_sqm: float
    total_energy_kwh: float
    energy_intensity_kwh_sqm: float
    emissions_kg_co2e: float
    baseline_expected_kwh: float
    deviation_pct: float
    anomaly_count: int
    recommendations_count: int
    verified_savings_kwh: float


class SustainabilityTrendPoint(BaseModel):
    """Single timeseries interval point for sustainability trends."""
    timestamp: datetime
    actual_kwh: float
    baseline_kwh: float
    emissions_kg_co2e: float
    energy_intensity_kwh_sqm: float
    is_anomaly: bool = False


class SustainabilityTrendsResponse(BaseModel):
    """Timeseries trends response with metadata."""
    building_id: Optional[int] = None
    building_name: Optional[str] = None
    granularity: str = "daily"
    trends: List[SustainabilityTrendPoint]


class CarbonFootprintResponse(BaseModel):
    """Detailed carbon footprint analysis and environmental equivalencies."""
    scope_boundary_notice: str = (
        "Accounting Scope: Scope 2 (Location-Based Electricity Consumption). "
        "Scope 1 (Direct Fuel Combustion) and Scope 3 (Commute / Value Chain) are outside sub-metering boundary."
    )
    emissions_factor: EmissionsFactorInfo
    total_emissions_kg_co2e: float
    total_emissions_tonnes_co2e: float
    building_breakdown: List[Dict[str, Any]]
    equivalencies: Dict[str, Any]


class SustainabilityTargetBase(BaseModel):
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    building_id: Optional[int] = None
    metric_type: str = "electricity_kwh"
    target_reduction_pct: float = Field(..., gt=0.0, le=100.0)
    baseline_period_start: datetime
    baseline_period_end: datetime
    baseline_value: float = Field(..., gt=0.0)
    target_completion_date: datetime


class SustainabilityTargetCreate(SustainabilityTargetBase):
    pass


class SustainabilityTargetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_reduction_pct: Optional[float] = None
    status: Optional[str] = None
    target_completion_date: Optional[datetime] = None


class SustainabilityTargetResponse(SustainabilityTargetBase):
    id: int
    current_measured_progress_pct: float
    current_measured_value: Optional[float] = None
    status: str
    last_calculated_at: datetime
    created_at: datetime
    updated_at: datetime
    building_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SustainabilityVerificationCreate(BaseModel):
    recommendation_id: Optional[int] = None
    baseline_period_start: Optional[datetime] = None
    baseline_period_end: Optional[datetime] = None
    post_action_period_start: Optional[datetime] = None
    post_action_period_end: Optional[datetime] = None
    verification_criteria: Optional[str] = None
    notes: Optional[str] = None


class SustainabilityVerificationResponse(BaseModel):
    id: int
    recommendation_id: int
    recommendation_title: Optional[str] = None
    building_name: Optional[str] = None
    baseline_period_start: datetime
    baseline_period_end: datetime
    baseline_avg_kwh: float
    post_action_period_start: datetime
    post_action_period_end: datetime
    post_action_avg_kwh: float
    observed_reduction_kwh: float
    observed_reduction_pct: float
    cost_savings_inr: float
    emissions_reduction_kg_co2e: float
    verification_status: str
    verification_criteria: str
    verified_by: str
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SustainabilityReportResponse(BaseModel):
    """Consolidated institutional sustainability report."""
    report_title: str = "CIT Coimbatore - Campus Energy & Sustainability Audit Report"
    generated_at: datetime
    reporting_period_start: Optional[datetime] = None
    reporting_period_end: Optional[datetime] = None
    data_provenance_disclaimer: str
    emissions_factor_provenance: EmissionsFactorInfo
    summary_metrics: SustainabilitySummaryResponse
    building_benchmarks: List[BuildingSustainabilityItem]
    targets_status: List[SustainabilityTargetResponse]
    verified_savings_ledger: List[SustainabilityVerificationResponse]
    methodology_notes: List[str]


class EnergyWasteEventItem(BaseModel):
    """Identified avoidable energy waste observation."""
    id: int
    reading_id: int
    building_id: int
    building_name: str
    building_code: str
    timestamp: datetime
    actual_kwh: float
    expected_kwh: float
    waste_kwh: float
    waste_cost_inr: float
    avoidable_emissions_kg_co2e: float
    waste_category: str  # 'after_hours_leakage', 'excess_baseload', 'equipment_surge'
    severity: str
    confidence: str
    explanation: str


class WhatIfScenarioRequest(BaseModel):
    """Input parameters for hypothetical sustainability interventions."""
    building_id: Optional[int] = None
    scenario_type: str = "solar_pv"  # 'solar_pv', 'led_retrofit', 'hvac_optimization', 'curfew_standby'
    efficiency_improvement_pct: Optional[float] = 10.0
    solar_capacity_kw: Optional[float] = 50.0
    grid_tariff_inr: Optional[float] = 7.50
    grid_emission_factor: Optional[float] = 0.716


class WhatIfScenarioResponse(BaseModel):
    """Simulated outcome of hypothetical decarbonization scenario."""
    scenario_type: str
    simulation_label: str
    building_name: str
    baseline_annual_kwh: float
    simulated_annual_savings_kwh: float
    simulated_savings_pct: float
    annual_cost_savings_inr: float
    annual_avoided_emissions_kg_co2e: float
    annual_avoided_emissions_tonnes: float
    estimated_payback_years: Optional[float] = None
    assumptions_summary: List[str]
    disclaimer: str

