"""Tests for database schema integrity, models, and synthetic seed data."""
import pytest
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models import (
    Building, EquipmentProfile, WeatherObservation,
    OccupancyRecord, EnergyReading
)


@pytest.fixture(scope="module")
def db_session():
    """Provide a database session for testing."""
    session = SessionLocal()
    yield session
    session.close()


def test_seeded_buildings(db_session):
    """Verify CIT prototype buildings are populated with valid metadata."""
    buildings = db_session.query(Building).all()
    assert len(buildings) >= 6
    
    codes = {b.code for b in buildings}
    expected_codes = {"CIT-MAIN", "CIT-IT", "CIT-ACAD", "CIT-LAB", "CIT-LIB", "CIT-WORK"}
    assert expected_codes.issubset(codes)

    for b in buildings:
        assert b.name is not None
        assert b.category is not None
        assert b.is_active is True
        assert b.meter_identifier is not None


def test_equipment_profiles(db_session):
    """Verify equipment profiles are linked to buildings."""
    equipment = db_session.query(EquipmentProfile).all()
    assert len(equipment) > 0
    for eq in equipment:
        assert eq.building_id is not None
        assert eq.equipment_category is not None


def test_readings_and_context_integrity(db_session):
    """Verify energy readings count and relationship integrity."""
    reading_count = db_session.query(func.count(EnergyReading.id)).scalar()
    assert reading_count >= 6480
    synthetic_count = db_session.query(func.count(EnergyReading.id)).filter(EnergyReading.is_synthetic.is_(True)).scalar()
    assert synthetic_count == 6480

    sample = db_session.query(EnergyReading).first()
    assert sample is not None
    assert sample.energy_kwh > 0
    assert sample.is_synthetic is True
    assert sample.data_source == "synthetic_seed"
    assert sample.meter_interval_minutes == 60
    assert sample.building is not None


def test_weather_and_occupancy_records(db_session):
    """Verify weather and occupancy datasets are populated."""
    weather_count = db_session.query(func.count(WeatherObservation.id)).scalar()
    occupancy_count = db_session.query(func.count(OccupancyRecord.id)).scalar()
    
    # 45 days * 24 hours = 1080 weather observations
    assert weather_count == 1080
    # 1080 hours * 6 buildings = 6480 occupancy records
    assert occupancy_count == 6480


def test_injected_anomaly_scenarios(db_session):
    """Verify the deliberately injected anomaly test cases are present."""
    anomalies = (
        db_session.query(EnergyReading)
        .filter(EnergyReading.notes.isnot(None))
        .filter(EnergyReading.notes.like("INJECTED_ANOMALY%"))
        .all()
    )
    assert len(anomalies) >= 4

    notes_text = " ".join([a.notes for a in anomalies])
    assert "Weekend HVAC" in notes_text
    assert "overnight" in notes_text
    assert "meter failure" in notes_text
    assert "thermal surge" in notes_text

