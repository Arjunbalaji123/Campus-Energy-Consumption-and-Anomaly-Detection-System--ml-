"""FastAPI router for CIT Building Registry endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.building import (
    BuildingResponse, BuildingCreate, BuildingUpdate,
    EquipmentProfileResponse, EquipmentProfileCreate
)
from app.services import building_service

router = APIRouter(prefix="/buildings", tags=["Buildings"])


@router.get("", response_model=List[BuildingResponse])
def list_buildings(
    active_only: bool = Query(True, description="Filter only active buildings"),
    category: Optional[str] = Query(None, description="Filter by building category"),
    db: Session = Depends(get_db)
):
    """List all registered campus buildings with optional filtering."""
    return building_service.get_buildings(db, active_only=active_only, category=category)


@router.post("", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
def create_building(
    data: BuildingCreate,
    db: Session = Depends(get_db)
):
    """Register a new campus building."""
    return building_service.create_building(db, data)


@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(
    building_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed profile and equipment configuration for a specific building."""
    return building_service.get_building_by_id(db, building_id)


@router.put("/{building_id}", response_model=BuildingResponse)
def update_building(
    building_id: int,
    data: BuildingUpdate,
    db: Session = Depends(get_db)
):
    """Update metadata, floor area, capacity, or operating hours of a building."""
    return building_service.update_building(db, building_id, data)


@router.delete("/{building_id}", response_model=BuildingResponse)
def deactivate_building(
    building_id: int,
    db: Session = Depends(get_db)
):
    """Soft-delete / deactivate a building registry entry."""
    return building_service.deactivate_building(db, building_id)


@router.post("/{building_id}/equipment", response_model=EquipmentProfileResponse, status_code=status.HTTP_201_CREATED)
def add_equipment(
    building_id: int,
    data: EquipmentProfileCreate,
    db: Session = Depends(get_db)
):
    """Add an electrical load or equipment profile to a building."""
    return building_service.add_equipment_profile(db, building_id, data)

