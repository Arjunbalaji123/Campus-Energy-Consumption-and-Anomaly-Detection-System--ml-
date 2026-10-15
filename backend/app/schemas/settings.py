"""Pydantic schemas for System Configuration and Calibrated Settings."""
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ThresholdUpdateRequest(BaseModel):
    warning_threshold: float = Field(..., ge=0.05, le=1.0, description="Warning threshold fraction (e.g. 0.25 = 25%)")
    critical_threshold: float = Field(..., ge=0.10, le=2.0, description="Critical threshold fraction (e.g. 0.50 = 50%)")

    @field_validator("critical_threshold")
    @classmethod
    def validate_threshold_order(cls, v: float, info) -> float:
        warn = info.data.get("warning_threshold")
        if warn is not None and v <= warn:
            raise ValueError("Critical threshold must be strictly greater than warning threshold.")
        return v


class SystemSettingsResponse(BaseModel):
    project_name: str
    environment: str
    debug: bool
    api_version: str
    anomaly_thresholds: Dict[str, float]
    building_categories: List[str]
    coimbatore_season_mapping: Dict[str, Any]
    active_models: Dict[str, str]

