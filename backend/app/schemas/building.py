"""Pydantic schemas for Building Registry and Equipment Profiles."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class EquipmentProfileBase(BaseModel):
    equipment_category: str = Field(..., max_length=100, description="Category of equipment, e.g. 'Chiller Plant'")
    rated_power_kw: Optional[float] = Field(None, ge=0.0, description="Rated electrical power in kW if known")
    count: int = Field(1, ge=1, description="Quantity of units installed")
    operating_schedule: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class EquipmentProfileCreate(EquipmentProfileBase):
    pass


class EquipmentProfileResponse(EquipmentProfileBase):
    id: int
    building_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildingBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Building name, e.g. 'Department of IT'")
    code: str = Field(..., min_length=2, max_length=20, description="Unique code, e.g. 'CIT-IT'")
    category: str = Field(
        ...,
        description="Building category, e.g. 'Main Block', 'IT Block', 'Academic Block', 'Laboratory Block', 'Library', 'Administration Block', 'Workshop / Equipment Block', 'Other Campus Buildings'"
    )
    floors: Optional[int] = Field(None, ge=1, le=50, description="Number of floors, if known")
    floor_area_sqm: Optional[float] = Field(None, ge=10.0, description="Floor area in square metres, if known")
    max_capacity: Optional[int] = Field(None, ge=1, description="Maximum occupant capacity, if known")
    operating_hours: Optional[str] = Field("08:30 - 17:00", max_length=50)
    operating_days: Optional[str] = Field("Mon - Fri", max_length=50)
    has_hvac: bool = Field(False, description="Whether building has HVAC or AC installed")
    lighting_type: Optional[str] = Field(None, max_length=100)
    meter_identifier: Optional[str] = Field(None, max_length=50, description="Hardware meter ID, if known")
    notes: Optional[str] = None
    is_active: bool = True


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[str] = None
    floors: Optional[int] = Field(None, ge=1, le=50)
    floor_area_sqm: Optional[float] = Field(None, ge=10.0)
    max_capacity: Optional[int] = Field(None, ge=1)
    operating_hours: Optional[str] = None
    operating_days: Optional[str] = None
    has_hvac: Optional[bool] = None
    lighting_type: Optional[str] = None
    meter_identifier: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class BuildingResponse(BuildingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    equipment_profiles: List[EquipmentProfileResponse] = []

    model_config = ConfigDict(from_attributes=True)

