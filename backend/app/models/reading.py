"""SQLAlchemy ORM models for Energy Readings, Weather, and Occupancy."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class WeatherObservation(Base):
    """Ambient weather observations for Coimbatore campus context."""
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    outdoor_temp_c = Column(Float, nullable=False)
    relative_humidity = Column(Float, nullable=True)
    weather_condition = Column(String(50), nullable=True)  # 'Clear', 'Rainy', 'Cloudy', 'Humid'
    rainfall_mm = Column(Float, nullable=True, default=0.0)
    season = Column(String(50), nullable=False)  # 'Winter', 'Summer', 'SW_Monsoon', 'NE_Monsoon'
    is_synthetic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    readings = relationship("EnergyReading", back_populates="weather")

    def __repr__(self):
        return f"<WeatherObservation(id={self.id}, ts='{self.timestamp}', temp={self.outdoor_temp_c}°C, season='{self.season}')>"


class OccupancyRecord(Base):
    """Occupancy counts and load percentages per building."""
    __tablename__ = "occupancy_records"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    headcount = Column(Integer, nullable=True)
    occupancy_pct = Column(Float, nullable=True)  # 0.0 to 100.0%
    is_estimated = Column(Boolean, default=False, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    building = relationship("Building", back_populates="occupancy_records")
    readings = relationship("EnergyReading", back_populates="occupancy")

    __table_args__ = (
        Index("idx_occupancy_bld_ts", "building_id", "timestamp"),
    )

    def __repr__(self):
        return f"<OccupancyRecord(id={self.id}, building_id={self.building_id}, headcount={self.headcount})>"


class EnergyReading(Base):
    """Energy Consumption meter readings (kWh) with context references."""
    __tablename__ = "energy_readings"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    energy_kwh = Column(Float, nullable=False)
    meter_interval_minutes = Column(Integer, default=60, nullable=False)
    
    # Optional Context Relationships (Nullable so missing context never prevents recording energy)
    weather_id = Column(Integer, ForeignKey("weather_observations.id", ondelete="SET NULL"), nullable=True, index=True)
    occupancy_id = Column(Integer, ForeignKey("occupancy_records.id", ondelete="SET NULL"), nullable=True, index=True)

    # Contextual Fields directly entered by user if no separate sensor table record
    indoor_temp_c = Column(Float, nullable=True)
    outdoor_temp_c = Column(Float, nullable=True)
    relative_humidity = Column(Float, nullable=True)
    occupancy_count = Column(Integer, nullable=True)
    
    # Operational Classification
    day_type = Column(String(50), default="working_day", nullable=False)  # 'working_day', 'weekend', 'holiday', 'special_event'
    operating_status = Column(String(50), default="normal", nullable=False)  # 'normal', 'reduced', 'closed', 'exam', 'maintenance'
    hvac_status = Column(String(50), nullable=True)  # 'on', 'off', 'partial', 'unknown'
    
    # Provenance and Financials
    is_synthetic = Column(Boolean, default=False, nullable=False)
    data_source = Column(String(50), default="manual", nullable=False)  # 'manual', 'csv_import', 'synthetic_seed'
    tariff_rate = Column(Float, nullable=True)  # in INR ₹/kWh
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    building = relationship("Building", back_populates="readings")
    weather = relationship("WeatherObservation", back_populates="readings")
    occupancy = relationship("OccupancyRecord", back_populates="readings")
    predictions = relationship("Prediction", back_populates="reading", cascade="all, delete-orphan")
    anomaly_events = relationship("AnomalyEvent", back_populates="reading", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_reading_bld_ts", "building_id", "timestamp"),
    )

    def __repr__(self):
        return f"<EnergyReading(id={self.id}, building_id={self.building_id}, ts='{self.timestamp}', kWh={self.energy_kwh})>"

