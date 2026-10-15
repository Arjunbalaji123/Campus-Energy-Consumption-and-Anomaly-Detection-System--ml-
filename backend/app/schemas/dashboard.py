"""Pydantic schemas for Consolidated Dashboard Analytics and Overview."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BuildingEnergyStat(BaseModel):
    building_id: int
    building_name: str
    building_code: str
    building_category: str
    total_energy_kwh: float
    avg_hourly_kwh: float
    reading_count: int
    anomaly_count: int


class RecentAlertItem(BaseModel):
    anomaly_id: int
    reading_id: int
    building_name: str
    building_code: str
    timestamp: datetime
    actual_energy_kwh: float
    predicted_energy_kwh: Optional[float] = None
    residual_kwh: Optional[float] = None
    deviation_pct: Optional[float] = None
    severity: str
    detection_method: str
    status: str


class DashboardOverviewResponse(BaseModel):
    total_energy_kwh: float
    total_cost_inr: float
    total_readings: int
    total_buildings: int
    active_anomalies_count: int
    anomaly_severity_breakdown: Dict[str, int]
    building_consumption: List[BuildingEnergyStat]
    recent_alerts: List[RecentAlertItem]
    model_status: Dict[str, Any]
    server_time: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    energy_kwh: float
    predicted_kwh: Optional[float] = None
    residual_kwh: Optional[float] = None
    is_anomaly: bool = False
    severity: Optional[str] = None


class DiurnalPoint(BaseModel):
    hour: int
    working_day_avg: float
    weekend_avg: float


class DashboardAnalyticsResponse(BaseModel):
    building_id: Optional[int] = None
    building_name: Optional[str] = None
    building_code: Optional[str] = None
    timeseries: List[TimeSeriesPoint]
    diurnal_profile: List[DiurnalPoint]

    model_config = ConfigDict(from_attributes=True)
