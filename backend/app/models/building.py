"""SQLAlchemy ORM models for Campus Buildings and Equipment Profiles."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Building(Base):
    """Campus Building Registry entity.
    
    Represents physical infrastructure at CIT Coimbatore.
    """
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False, index=True)  # e.g., 'IT Block', 'Laboratory Block'
    floors = Column(Integer, nullable=True)
    floor_area_sqm = Column(Float, nullable=True)
    max_capacity = Column(Integer, nullable=True)  # Max occupancy
    operating_hours = Column(String(50), nullable=True, default="08:30 - 17:00")
    operating_days = Column(String(50), nullable=True, default="Mon - Fri")
    has_hvac = Column(Boolean, default=False, nullable=False)
    lighting_type = Column(String(100), nullable=True)  # e.g., 'LED Smart Dimming', 'Fluorescent'
    meter_identifier = Column(String(50), nullable=True, unique=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    readings = relationship("EnergyReading", back_populates="building", cascade="all, delete-orphan")
    occupancy_records = relationship("OccupancyRecord", back_populates="building", cascade="all, delete-orphan")
    equipment_profiles = relationship("EquipmentProfile", back_populates="building", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="building", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Building(id={self.id}, code='{self.code}', name='{self.name}', category='{self.category}')>"


class EquipmentProfile(Base):
    """Major electrical equipment and load profiles associated with a building."""
    __tablename__ = "equipment_profiles"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True)
    equipment_category = Column(String(100), nullable=False)  # e.g., 'Chiller Plant', 'Computer Lab PCs'
    rated_power_kw = Column(Float, nullable=True)
    count = Column(Integer, default=1, nullable=False)
    operating_schedule = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    building = relationship("Building", back_populates="equipment_profiles")

    def __repr__(self):
        return f"<EquipmentProfile(id={self.id}, building_id={self.building_id}, category='{self.equipment_category}')>"

