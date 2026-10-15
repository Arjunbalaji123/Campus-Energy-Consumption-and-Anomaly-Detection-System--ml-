"""Service layer implementing business logic for Manual Energy Entry, Search, and CSV I/O."""
import io
import csv
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.building import Building
from app.models.reading import EnergyReading
from app.schemas.reading import EnergyReadingCreate, EnergyReadingUpdate, EnergyReadingResponse, CSVImportSummaryResponse
from app.services.building_service import get_building_by_id, get_building_by_code


def create_energy_reading(db: Session, data: EnergyReadingCreate) -> EnergyReading:
    """Create a manual energy observation with duplicate checking and building validation."""
    building = get_building_by_id(db, data.building_id)

    # Check for duplicate observation for the same building at the same timestamp
    existing = (
        db.query(EnergyReading)
        .filter(
            EnergyReading.building_id == data.building_id,
            EnergyReading.timestamp == data.timestamp
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"An observation for building '{building.name}' ({building.code}) "
                f"at timestamp '{data.timestamp}' already exists (ID: {existing.id})."
            )
        )

    reading = EnergyReading(
        building_id=data.building_id,
        timestamp=data.timestamp,
        energy_kwh=data.energy_kwh,
        meter_interval_minutes=data.meter_interval_minutes,
        indoor_temp_c=data.indoor_temp_c,
        outdoor_temp_c=data.outdoor_temp_c,
        relative_humidity=data.relative_humidity,
        occupancy_count=data.occupancy_count,
        day_type=data.day_type,
        operating_status=data.operating_status,
        hvac_status=data.hvac_status,
        tariff_rate=data.tariff_rate,
        data_source=data.data_source,
        is_synthetic=(data.data_source == "synthetic_seed"),
        notes=data.notes,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def get_energy_reading_by_id(db: Session, reading_id: int) -> EnergyReading:
    """Retrieve an energy reading by primary key or raise 404."""
    reading = db.query(EnergyReading).filter(EnergyReading.id == reading_id).first()
    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Energy reading with ID {reading_id} not found."
        )
    return reading


def get_readings_paginated(
    db: Session,
    building_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    day_type: Optional[str] = None,
    is_synthetic: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[int, List[EnergyReadingResponse]]:
    """Query energy observations with multi-field filtering and pagination."""
    query = db.query(EnergyReading).join(Building, EnergyReading.building_id == Building.id)

    if building_id:
        query = query.filter(EnergyReading.building_id == building_id)
    if start_date:
        query = query.filter(EnergyReading.timestamp >= start_date)
    if end_date:
        query = query.filter(EnergyReading.timestamp <= end_date)
    if day_type:
        query = query.filter(EnergyReading.day_type == day_type)
    if is_synthetic is not None:
        query = query.filter(EnergyReading.is_synthetic.is_(is_synthetic))

    total = query.count()
    offset = (page - 1) * page_size
    readings = query.order_by(EnergyReading.timestamp.desc()).offset(offset).limit(page_size).all()

    # Enrich responses with building details
    enriched = []
    for r in readings:
        resp = EnergyReadingResponse(
            id=r.id,
            building_id=r.building_id,
            timestamp=r.timestamp,
            energy_kwh=r.energy_kwh,
            meter_interval_minutes=r.meter_interval_minutes,
            indoor_temp_c=r.indoor_temp_c,
            outdoor_temp_c=r.outdoor_temp_c,
            relative_humidity=r.relative_humidity,
            occupancy_count=r.occupancy_count,
            day_type=r.day_type,
            operating_status=r.operating_status,
            hvac_status=r.hvac_status,
            tariff_rate=r.tariff_rate,
            data_source=r.data_source,
            is_synthetic=r.is_synthetic,
            notes=r.notes,
            created_at=r.created_at,
            building_name=r.building.name if r.building else None,
            building_code=r.building.code if r.building else None,
        )
        enriched.append(resp)

    return total, enriched


def update_energy_reading(
    db: Session,
    reading_id: int,
    data: EnergyReadingUpdate
) -> EnergyReading:
    """Update an existing energy reading."""
    reading = get_energy_reading_by_id(db, reading_id)

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(reading, field, val)

    db.commit()
    db.refresh(reading)
    return reading


def delete_energy_reading(db: Session, reading_id: int) -> bool:
    """Permanently delete an energy reading."""
    reading = get_energy_reading_by_id(db, reading_id)
    db.delete(reading)
    db.commit()
    return True


def export_readings_to_csv(
    db: Session,
    building_id: Optional[int] = None,
    limit: int = 5000
) -> str:
    """Generate CSV text output of energy records for analysis or auditing."""
    query = db.query(EnergyReading).join(Building, EnergyReading.building_id == Building.id)
    if building_id:
        query = query.filter(EnergyReading.building_id == building_id)

    records = query.order_by(EnergyReading.timestamp.desc()).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "building_code", "building_name", "timestamp", "energy_kwh",
        "meter_interval_minutes", "outdoor_temp_c", "relative_humidity",
        "occupancy_count", "day_type", "operating_status", "hvac_status",
        "tariff_rate", "data_source", "is_synthetic", "notes"
    ])

    for r in records:
        writer.writerow([
            r.id,
            r.building.code if r.building else "",
            r.building.name if r.building else "",
            r.timestamp.isoformat(),
            r.energy_kwh,
            r.meter_interval_minutes,
            r.outdoor_temp_c or "",
            r.relative_humidity or "",
            r.occupancy_count or "",
            r.day_type,
            r.operating_status,
            r.hvac_status or "",
            r.tariff_rate or "",
            r.data_source,
            r.is_synthetic,
            r.notes or "",
        ])

    return output.getvalue()


def import_readings_from_csv(db: Session, csv_content: str) -> CSVImportSummaryResponse:
    """Parse, validate, and bulk-import energy readings from a CSV upload."""
    reader = csv.DictReader(io.StringIO(csv_content))
    total = 0
    imported = 0
    skipped = 0
    errors = []

    building_cache = {b.code: b.id for b in db.query(Building).all()}

    for row_idx, row in enumerate(reader, start=1):
        total += 1
        try:
            b_code = row.get("building_code", "").strip().upper()
            if not b_code or b_code not in building_cache:
                errors.append(f"Row {row_idx}: Unknown building code '{b_code}'")
                continue

            building_id = building_cache[b_code]
            ts_str = row.get("timestamp", "").strip()
            # Parse ISO or standard format
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

            # Check duplicate
            existing = (
                db.query(EnergyReading.id)
                .filter(EnergyReading.building_id == building_id, EnergyReading.timestamp == ts)
                .first()
            )
            if existing:
                skipped += 1
                continue

            kwh = float(row.get("energy_kwh", 0.0))
            if kwh < 0:
                errors.append(f"Row {row_idx}: Negative energy_kwh ({kwh})")
                continue

            reading = EnergyReading(
                building_id=building_id,
                timestamp=ts,
                energy_kwh=kwh,
                meter_interval_minutes=int(row.get("meter_interval_minutes", 60)),
                outdoor_temp_c=float(row["outdoor_temp_c"]) if row.get("outdoor_temp_c") else None,
                relative_humidity=float(row["relative_humidity"]) if row.get("relative_humidity") else None,
                occupancy_count=int(row["occupancy_count"]) if row.get("occupancy_count") else None,
                day_type=row.get("day_type", "working_day"),
                operating_status=row.get("operating_status", "normal"),
                hvac_status=row.get("hvac_status", "unknown"),
                tariff_rate=float(row["tariff_rate"]) if row.get("tariff_rate") else None,
                data_source="csv_import",
                is_synthetic=False,
                notes=row.get("notes"),
            )
            db.add(reading)
            imported += 1

            if imported % 100 == 0:
                db.flush()

        except Exception as e:
            errors.append(f"Row {row_idx}: Parse error: {str(e)}")

    db.commit()
    return CSVImportSummaryResponse(
        total_rows=total,
        imported=imported,
        skipped_duplicates=skipped,
        errors=errors[:10], # Truncate error display if huge
    )

