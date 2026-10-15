"""Synthetic Data Generator & Database Seeder for CIT Coimbatore Campus Energy Prototype.

Generates realistic hourly energy, weather, and occupancy observations with
accurate seasonal profiles for Coimbatore and deliberately injected anomaly scenarios.
All records are explicitly tagged as synthetic (`is_synthetic = True`).
"""
import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.database import SessionLocal, engine
from app.models import (
    Base, Building, EquipmentProfile, WeatherObservation,
    OccupancyRecord, EnergyReading
)

# Set deterministic random seed for reproducible academic testing
random.seed(42)
np.random.seed(42)

# CIT Coimbatore Prototype Buildings Definition
CIT_BUILDINGS = [
    {
        "name": "Main Administrative Block",
        "code": "CIT-MAIN",
        "category": "Main Block",
        "floors": 4,
        "floor_area_sqm": 6200.0,
        "max_capacity": 650,
        "operating_hours": "08:30 - 17:30",
        "operating_days": "Mon - Fri",
        "has_hvac": True,
        "lighting_type": "LED Smart Fixtures",
        "meter_identifier": "MTR-CIT-MAIN-01",
        "notes": "Houses principal offices, conference halls, and central administration.",
        "base_standby_kwh": 22.0,
        "peak_operational_kwh": 95.0,
    },
    {
        "name": "Department of Information Technology Block",
        "code": "CIT-IT",
        "category": "IT Block",
        "floors": 5,
        "floor_area_sqm": 8500.0,
        "max_capacity": 1200,
        "operating_hours": "08:00 - 18:30",
        "operating_days": "Mon - Sat",
        "has_hvac": True,
        "lighting_type": "Fluorescent & LED Mix",
        "meter_identifier": "MTR-CIT-IT-01",
        "notes": "Continuous server room cooling, 8 large computer laboratories.",
        "base_standby_kwh": 38.0,
        "peak_operational_kwh": 145.0,
    },
    {
        "name": "Dr. V. Selladurai Academic Complex",
        "code": "CIT-ACAD",
        "category": "Academic Block",
        "floors": 4,
        "floor_area_sqm": 9200.0,
        "max_capacity": 1800,
        "operating_hours": "08:30 - 16:45",
        "operating_days": "Mon - Fri",
        "has_hvac": False,
        "lighting_type": "LED Tube Lighting",
        "meter_identifier": "MTR-CIT-ACAD-01",
        "notes": "Lecture halls, tutorial rooms, seminar halls with ceiling fans.",
        "base_standby_kwh": 18.0,
        "peak_operational_kwh": 85.0,
    },
    {
        "name": "Central Science & Engineering Laboratories",
        "code": "CIT-LAB",
        "category": "Laboratory Block",
        "floors": 3,
        "floor_area_sqm": 7100.0,
        "max_capacity": 850,
        "operating_hours": "08:30 - 17:30",
        "operating_days": "Mon - Sat",
        "has_hvac": True,
        "lighting_type": "Industrial Grade Fluorescent",
        "meter_identifier": "MTR-CIT-LAB-01",
        "notes": "Chemistry hoods, physics equipment, materials testing apparatus.",
        "base_standby_kwh": 25.0,
        "peak_operational_kwh": 120.0,
    },
    {
        "name": "Central Library & Digital Knowledge Centre",
        "code": "CIT-LIB",
        "category": "Library",
        "floors": 3,
        "floor_area_sqm": 4800.0,
        "max_capacity": 900,
        "operating_hours": "08:00 - 20:00",
        "operating_days": "Mon - Sun",
        "has_hvac": True,
        "lighting_type": "Daylight Harvesting LED",
        "meter_identifier": "MTR-CIT-LIB-01",
        "notes": "Extended operating hours for student reading and digital terminals.",
        "base_standby_kwh": 20.0,
        "peak_operational_kwh": 78.0,
    },
    {
        "name": "Mechanical & Industrial Workshop Block",
        "code": "CIT-WORK",
        "category": "Workshop / Equipment Block",
        "floors": 2,
        "floor_area_sqm": 5400.0,
        "max_capacity": 450,
        "operating_hours": "08:30 - 16:30",
        "operating_days": "Mon - Fri",
        "has_hvac": False,
        "lighting_type": "High-Bay Sodium & LED",
        "meter_identifier": "MTR-CIT-WORK-01",
        "notes": "Lathes, CNC machines, welding, and foundry training bays.",
        "base_standby_kwh": 12.0,
        "peak_operational_kwh": 110.0,
    },
]


def get_coimbatore_season(month: int) -> tuple[str, float, float, float]:
    """Map calendar month to Coimbatore climatic season, temperature range, and humidity.
    
    Returns: (season_name, min_temp, max_temp, base_humidity)
    """
    if month in [12, 1, 2]:
        return "Winter", 19.0, 30.0, 55.0
    elif month in [3, 4, 5]:
        return "Summer", 24.0, 38.0, 48.0
    elif month in [6, 7, 8]:
        return "SW_Monsoon", 22.0, 31.0, 72.0
    else:
        return "NE_Monsoon", 22.0, 30.0, 80.0


def is_tamil_nadu_holiday(dt: datetime) -> bool:
    """Simulate key academic and state holidays in Tamil Nadu."""
    m, d = dt.month, dt.day
    holidays = [
        (1, 14), (1, 15), (1, 16), # Pongal / Thiruvalluvar Day
        (1, 26),                   # Republic Day
        (4, 14),                   # Tamil New Year
        (5, 1),                    # May Day
        (8, 15),                   # Independence Day
        (10, 2),                   # Gandhi Jayanti
        (10, 31),                  # Deepavali / Diwali approximate
        (12, 25),                  # Christmas
    ]
    return (m, d) in holidays


def generate_seed_data(days: int = 45):
    """Generate synthetic hourly data for CIT Coimbatore prototype."""
    print(f"Generating {days} days of hourly synthetic observations...")
    db = SessionLocal()

    # Clear existing data to allow clean re-seeding
    db.query(EnergyReading).delete()
    db.query(OccupancyRecord).delete()
    db.query(WeatherObservation).delete()
    db.query(EquipmentProfile).delete()
    db.query(Building).delete()
    db.commit()

    # 1. Insert Buildings
    building_objs = {}
    for b_data in CIT_BUILDINGS:
        b = Building(
            name=b_data["name"],
            code=b_data["code"],
            category=b_data["category"],
            floors=b_data["floors"],
            floor_area_sqm=b_data["floor_area_sqm"],
            max_capacity=b_data["max_capacity"],
            operating_hours=b_data["operating_hours"],
            operating_days=b_data["operating_days"],
            has_hvac=b_data["has_hvac"],
            lighting_type=b_data["lighting_type"],
            meter_identifier=b_data["meter_identifier"],
            notes=b_data["notes"],
            is_active=True,
        )
        db.add(b)
        db.flush()
        building_objs[b_data["code"]] = (b, b_data)

        # Add initial equipment profile
        if b_data["has_hvac"]:
            db.add(EquipmentProfile(
                building_id=b.id,
                equipment_category="Centralized Chiller / Split AC Units",
                rated_power_kw=45.0,
                count=4,
                operating_schedule="08:00 - 17:30 Working Days"
            ))
        db.add(EquipmentProfile(
            building_id=b.id,
            equipment_category="Lighting & Plug Loads",
            rated_power_kw=15.0,
            count=1,
            operating_schedule="Operational Hours"
        ))

    db.commit()
    print(f"Successfully seeded {len(CIT_BUILDINGS)} CIT buildings.")

    # 2. Generate Time Series
    start_time = datetime(2026, 8, 15, 0, 0, 0) # Academic session start
    total_hours = days * 24

    records_to_export = []

    for h_idx in range(total_hours):
        current_time = start_time + timedelta(hours=h_idx)
        hour = current_time.hour
        month = current_time.month
        weekday = current_time.weekday() # 0 = Mon, 6 = Sun
        is_weekend = weekday in [5, 6]
        is_holiday = is_tamil_nadu_holiday(current_time)

        if is_holiday:
            day_type = "holiday"
        elif is_weekend:
            day_type = "weekend"
        else:
            day_type = "working_day"

        # Coimbatore weather simulation
        season_name, min_t, max_t, base_hum = get_coimbatore_season(month)
        
        # Diurnal temperature cycle: lowest at 05:00, peak at 14:00
        temp_diurnal = np.sin((hour - 8) / 24.0 * 2 * np.pi)
        outdoor_temp = round(min_t + (max_t - min_t) * 0.5 * (1 + temp_diurnal) + np.random.normal(0, 0.7), 1)
        humidity = round(np.clip(base_hum - (temp_diurnal * 12) + np.random.normal(0, 2), 25, 95), 1)
        
        rainfall = 0.0
        weather_cond = "Clear"
        if "Monsoon" in season_name and random.random() < 0.25:
            rainfall = round(random.uniform(2.0, 18.0), 1)
            weather_cond = "Rainy"
        elif outdoor_temp > 33.0:
            weather_cond = "Hot / Sunny"

        # Create Weather Observation
        weather_obs = WeatherObservation(
            timestamp=current_time,
            outdoor_temp_c=outdoor_temp,
            relative_humidity=humidity,
            weather_condition=weather_cond,
            rainfall_mm=rainfall,
            season=season_name,
            is_synthetic=True,
        )
        db.add(weather_obs)
        db.flush()

        # 3. Simulate readings for each building
        for code, (b_obj, b_meta) in building_objs.items():
            base_kwh = b_meta["base_standby_kwh"]
            peak_kwh = b_meta["peak_operational_kwh"]
            max_cap = b_meta["max_capacity"]
            has_hvac = b_meta["has_hvac"]

            # Occupancy model
            if day_type == "working_day" and 8 <= hour <= 17:
                # Bell curve centered around 12:00
                occupancy_ratio = 0.75 + 0.2 * np.sin((hour - 8) / 9.0 * np.pi)
                op_status = "normal"
            elif day_type == "working_day" and (7 == hour or 18 <= hour <= 20):
                occupancy_ratio = 0.15
                op_status = "reduced"
            elif day_type == "weekend" and (code == "CIT-LIB" and 9 <= hour <= 18):
                # Library has weekend visitors
                occupancy_ratio = 0.40
                op_status = "normal"
            elif day_type == "weekend":
                occupancy_ratio = 0.03
                op_status = "closed"
            else:
                occupancy_ratio = 0.02
                op_status = "closed"

            headcount = int(max_cap * occupancy_ratio + np.random.normal(0, max_cap * 0.02))
            headcount = max(0, min(max_cap, headcount))
            occupancy_pct = round((headcount / max_cap) * 100, 1)

            # Create Occupancy Record
            occ_rec = OccupancyRecord(
                building_id=b_obj.id,
                timestamp=current_time,
                headcount=headcount,
                occupancy_pct=occupancy_pct,
                is_estimated=True,
                is_synthetic=True,
            )
            db.add(occ_rec)
            db.flush()

            # Thermodynamic energy consumption model
            # Base standby load + occupancy equipment load + cooling thermal load
            occ_load = (peak_kwh - base_kwh) * 0.5 * (headcount / max_cap)
            
            cooling_load = 0.0
            if has_hvac and op_status != "closed":
                cooling_load = max(0.0, (outdoor_temp - 24.0) * 2.8)
            
            noise = np.random.normal(0, 2.5)
            kwh = base_kwh + occ_load + cooling_load + noise
            kwh = max(base_kwh * 0.7, kwh) # Physical lower bound

            # Injected Anomaly Scenarios (deliberately crafted for testing)
            hvac_state = "on" if (has_hvac and op_status != "closed") else "off"
            anomaly_note = None

            # Scenario A: IT Block Weekend AC left running (Day 12, Sunday, 14:00)
            if code == "CIT-IT" and h_idx == (12 * 24 + 14):
                kwh = 168.5  # Surge from expected ~45 kWh
                hvac_state = "on"
                anomaly_note = "INJECTED_ANOMALY: Weekend HVAC left running at full power with low occupancy."

            # Scenario B: Laboratory Block Midnight Equipment left active (Day 25, Wednesday, 02:00)
            elif code == "CIT-LAB" and h_idx == (25 * 24 + 2):
                kwh = 98.0   # Surge from expected ~25 kWh
                anomaly_note = "INJECTED_ANOMALY: Heavy testing machinery active overnight outside operating hours."

            # Scenario C: Workshop Block Meter Trip / Drop (Day 32, Monday, 11:00)
            elif code == "CIT-WORK" and h_idx == (32 * 24 + 11):
                kwh = 2.1    # Drop from expected ~90 kWh
                anomaly_note = "INJECTED_ANOMALY: Plausible meter failure or tripped main circuit breaker."

            # Scenario D: Academic Block Heatwave surge (Day 40, Thursday, 14:00)
            elif code == "CIT-ACAD" and h_idx == (40 * 24 + 14):
                kwh = 132.0  # Spike due to severe heat load and fan usage
                anomaly_note = "INJECTED_ANOMALY: Extreme thermal surge in non-HVAC building."

            # Create Energy Reading
            reading = EnergyReading(
                building_id=b_obj.id,
                timestamp=current_time,
                energy_kwh=round(kwh, 2),
                meter_interval_minutes=60,
                weather_id=weather_obs.id,
                occupancy_id=occ_rec.id,
                indoor_temp_c=round(outdoor_temp - 3.5, 1) if has_hvac else outdoor_temp,
                outdoor_temp_c=outdoor_temp,
                relative_humidity=humidity,
                occupancy_count=headcount,
                day_type=day_type,
                operating_status=op_status,
                hvac_status=hvac_state,
                is_synthetic=True,
                data_source="synthetic_seed",
                tariff_rate=7.50, # Standard Tamil Nadu HT commercial institutional tariff ~₹7.50/kWh
                notes=anomaly_note,
            )
            db.add(reading)

            records_to_export.append({
                "timestamp": current_time,
                "building_code": code,
                "building_name": b_obj.name,
                "building_category": b_meta["category"],
                "floor_area_sqm": b_meta["floor_area_sqm"],
                "energy_kwh": round(kwh, 2),
                "outdoor_temp_c": outdoor_temp,
                "relative_humidity": humidity,
                "weather_condition": weather_cond,
                "season": season_name,
                "occupancy_count": headcount,
                "max_capacity": max_cap,
                "day_type": day_type,
                "operating_status": op_status,
                "has_hvac": has_hvac,
                "is_synthetic": True,
                "notes": anomaly_note or "",
            })

    db.commit()
    db.close()

    # Save to CSV for ML model training and external validation
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "synthetic_campus_energy.csv"))
    df = pd.DataFrame(records_to_export)
    df.to_csv(csv_path, index=False)
    print(f"Generated {len(df)} total hourly energy readings.")
    print(f"Saved dataset snapshot to: {csv_path}")


if __name__ == "__main__":
    generate_seed_data(days=45)

