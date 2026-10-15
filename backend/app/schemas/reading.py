"""Pydantic schemas for Manual Energy Reading Data Entry and Search."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EnergyReadingBase(BaseModel):
    building_id: int = Field(..., description="ID of the campus building")
    timestamp: datetime = Field(..., description="Observation date and time (ISO format)")
    energy_kwh: float = Field(..., ge=0.0, le=100000.0, description="Energy consumption in kWh")
    meter_interval_minutes: int = Field(60, ge=1, le=1440, description="Meter integration interval in minutes")

    # Optional Contextual Fields
    indoor_temp_c: Optional[float] = Field(None, ge=-10.0, le=60.0, description="Indoor temperature in °C if available")
    outdoor_temp_c: Optional[float] = Field(None, ge=-10.0, le=60.0, description="Outdoor ambient temperature in °C")
    relative_humidity: Optional[float] = Field(None, ge=0.0, le=100.0, description="Relative humidity in %")
    occupancy_count: Optional[int] = Field(None, ge=0, description="Headcount or people present during interval")

    # Operational Categorization
    day_type: str = Field("working_day", description="Day category: 'working_day', 'weekend', 'holiday', 'special_event'")
    operating_status: str = Field("normal", description="Operating state: 'normal', 'reduced', 'closed', 'exam', 'maintenance'")
    hvac_status: Optional[str] = Field("unknown", description="HVAC runtime status: 'on', 'off', 'partial', 'unknown'")

    # Financial & Provenance
    tariff_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Electricity tariff in ₹/kWh")
    data_source: str = Field("manual", description="Data provenance: 'manual', 'csv_import', 'synthetic_seed'")
    notes: Optional[str] = Field(None, max_length=500, description="Observer notes or unusual remarks")

    @field_validator("day_type")
    @classmethod
    def validate_day_type(cls, v: str) -> str:
        allowed = {"working_day", "weekend", "holiday", "special_event"}
        if v not in allowed:
            raise ValueError(f"day_type must be one of {allowed}")
        return v

    @field_validator("operating_status")
    @classmethod
    def validate_operating_status(cls, v: str) -> str:
        allowed = {"normal", "reduced", "closed", "exam", "maintenance"}
        if v not in allowed:
            raise ValueError(f"operating_status must be one of {allowed}")
        return v


class EnergyReadingCreate(EnergyReadingBase):
    pass


class EnergyReadingUpdate(BaseModel):
    energy_kwh: Optional[float] = Field(None, ge=0.0, le=100000.0)
    meter_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    indoor_temp_c: Optional[float] = Field(None, ge=-10.0, le=60.0)
    outdoor_temp_c: Optional[float] = Field(None, ge=-10.0, le=60.0)
    relative_humidity: Optional[float] = Field(None, ge=0.0, le=100.0)
    occupancy_count: Optional[int] = Field(None, ge=0)
    day_type: Optional[str] = None
    operating_status: Optional[str] = None
    hvac_status: Optional[str] = None
    tariff_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    notes: Optional[str] = None


class EnergyReadingResponse(EnergyReadingBase):
    id: int
    is_synthetic: bool
    created_at: datetime
    building_name: Optional[str] = None
    building_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedReadingsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[EnergyReadingResponse]


class CSVImportSummaryResponse(BaseModel):
    total_rows: int
    imported: int
    skipped_duplicates: int
    errors: List[str] = []

