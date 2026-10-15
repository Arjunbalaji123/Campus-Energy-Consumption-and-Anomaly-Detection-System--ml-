"""Service layer implementing business logic for CIT Building Registry."""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.building import Building, EquipmentProfile
from app.schemas.building import BuildingCreate, BuildingUpdate, EquipmentProfileCreate


def get_buildings(
    db: Session,
    active_only: bool = True,
    category: Optional[str] = None
) -> List[Building]:
    """Retrieve all campus buildings with optional filtering."""
    query = db.query(Building)
    if active_only:
        query = query.filter(Building.is_active.is_(True))
    if category:
        query = query.filter(Building.category == category)
    return query.order_by(Building.name.asc()).all()


def get_building_by_id(db: Session, building_id: int) -> Building:
    """Retrieve a building by its primary key or raise 404."""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with ID {building_id} not found."
        )
    return building


def get_building_by_code(db: Session, code: str) -> Optional[Building]:
    """Retrieve a building by unique campus code."""
    return db.query(Building).filter(Building.code == code).first()


def create_building(db: Session, data: BuildingCreate) -> Building:
    """Register a new building with duplicate code and name validation."""
    existing_code = get_building_by_code(db, data.code)
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Building with code '{data.code}' already exists."
        )

    existing_name = db.query(Building).filter(Building.name == data.name).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Building with name '{data.name}' already exists."
        )

    building = Building(
        name=data.name,
        code=data.code.upper(),
        category=data.category,
        floors=data.floors,
        floor_area_sqm=data.floor_area_sqm,
        max_capacity=data.max_capacity,
        operating_hours=data.operating_hours,
        operating_days=data.operating_days,
        has_hvac=data.has_hvac,
        lighting_type=data.lighting_type,
        meter_identifier=data.meter_identifier,
        notes=data.notes,
        is_active=data.is_active,
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


def update_building(db: Session, building_id: int, data: BuildingUpdate) -> Building:
    """Update building metadata with field-level validation."""
    building = get_building_by_id(db, building_id)

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(building, field, val)

    db.commit()
    db.refresh(building)
    return building


def deactivate_building(db: Session, building_id: int) -> Building:
    """Soft-delete (deactivate) a building without removing historical data."""
    building = get_building_by_id(db, building_id)
    building.is_active = False
    db.commit()
    db.refresh(building)
    return building


def add_equipment_profile(
    db: Session,
    building_id: int,
    data: EquipmentProfileCreate
) -> EquipmentProfile:
    """Attach an equipment profile to a building."""
    get_building_by_id(db, building_id) # Ensure building exists

    profile = EquipmentProfile(
        building_id=building_id,
        equipment_category=data.equipment_category,
        rated_power_kw=data.rated_power_kw,
        count=data.count,
        operating_schedule=data.operating_schedule,
        notes=data.notes,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

