"""Pydantic schemas for Evidence-Based Anomaly Explanations and Recommendations."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnomalyExplanationResponse(BaseModel):
    id: int
    anomaly_event_id: int
    primary_hypothesis: str
    evidence: Dict[str, Any] = Field(..., description="Structured dictionary of supporting physical facts")
    confidence: str = Field(..., description="'low', 'medium', or 'high'")
    data_to_confirm: Optional[str] = None
    recommended_next_action: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    id: int
    anomaly_event_id: int
    title: str
    priority: str = Field(..., description="'low', 'medium', 'high', 'critical'")
    supporting_evidence: str
    recommended_action: str
    responsible_role: str = Field("Facilities Staff", description="Assigned role: 'Facilities Staff', 'Energy Manager', 'Lab Technician'")
    follow_up_verification: Optional[str] = None
    status: str = Field("open", description="'open', 'investigating', 'resolved', 'dismissed'")
    estimated_savings_kwh: Optional[float] = Field(None, description="Estimated potential energy saving in kWh")
    building_name: Optional[str] = None
    building_code: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: 'open', 'investigating', 'resolved', 'dismissed'")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"open", "investigating", "resolved", "dismissed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class PaginatedRecommendationsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[RecommendationResponse]

