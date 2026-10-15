"""Pydantic schemas for Anomaly Detection Events and Status Management."""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnomalyExplanationItem(BaseModel):
    id: int
    anomaly_event_id: int
    primary_hypothesis: str
    evidence: Any = {}
    confidence: str
    data_to_confirm: Optional[str] = None
    recommended_next_action: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyRecommendationItem(BaseModel):
    id: int
    anomaly_event_id: int
    title: str
    priority: str
    supporting_evidence: str
    recommended_action: str
    responsible_role: str
    follow_up_verification: Optional[str] = None
    status: str
    estimated_savings_kwh: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyEventResponse(BaseModel):
    id: int
    reading_id: int
    prediction_id: Optional[int] = None
    building_id: int
    building_name: Optional[str] = None
    building_code: Optional[str] = None
    timestamp: datetime
    actual_energy_kwh: float
    predicted_energy_kwh: Optional[float] = None
    residual_kwh: Optional[float] = None
    deviation_pct: Optional[float] = None
    detection_method: str = Field(..., description="'residual', 'isolation_forest', or 'dual'")
    severity: str = Field(..., description="'normal', 'warning', or 'critical'")
    anomaly_score: Optional[float] = Field(None, description="Isolation Forest decision score or outlier indicator")
    status: str = Field("open", description="'open', 'investigating', 'resolved', 'dismissed'")
    detected_at: datetime

    # Forensic context from reading & building
    indoor_temp_c: Optional[float] = None
    outdoor_temp_c: Optional[float] = None
    relative_humidity: Optional[float] = None
    occupancy_count: Optional[int] = None
    max_capacity: Optional[int] = None
    day_type: Optional[str] = None
    operating_status: Optional[str] = None
    hvac_status: Optional[str] = None
    floor_area_sqm: Optional[float] = None

    explanations: List[AnomalyExplanationItem] = []
    recommendations: List[AnomalyRecommendationItem] = []

    model_config = ConfigDict(from_attributes=True)


class AnomalyStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: 'open', 'investigating', 'resolved', 'dismissed'")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"open", "investigating", "resolved", "dismissed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class PaginatedAnomaliesResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[AnomalyEventResponse]


class AnomalyScanSummaryResponse(BaseModel):
    total_scanned: int
    anomalies_detected: int
    warning_count: int
    critical_count: int
    dual_count: int
    message: str
