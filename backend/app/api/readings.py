"""FastAPI router for Manual Energy Data Entry, Search, and CSV Import/Export."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.datetime_utils import get_utc_now
from app.schemas.reading import (
    EnergyReadingCreate, EnergyReadingUpdate, EnergyReadingResponse,
    PaginatedReadingsResponse, CSVImportSummaryResponse
)
from app.services import reading_service

router = APIRouter(prefix="/readings", tags=["Energy Readings"])


@router.get("", response_model=PaginatedReadingsResponse)
def list_readings(
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    start_date: Optional[datetime] = Query(None, description="Filter observations from this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter observations until this timestamp"),
    day_type: Optional[str] = Query(None, description="Filter by 'working_day', 'weekend', 'holiday'"),
    is_synthetic: Optional[bool] = Query(None, description="Filter synthetic vs real observations"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve searchable, paginated energy records with contextual filtering."""
    total, items = reading_service.get_readings_paginated(
        db,
        building_id=building_id,
        start_date=start_date,
        end_date=end_date,
        day_type=day_type,
        is_synthetic=is_synthetic,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedReadingsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.post("", response_model=EnergyReadingResponse, status_code=status.HTTP_201_CREATED)
def submit_manual_reading(
    data: EnergyReadingCreate,
    db: Session = Depends(get_db)
):
    """Submit a single manual energy observation with duplicate-check validation."""
    reading = reading_service.create_energy_reading(db, data)
    return EnergyReadingResponse(
        id=reading.id,
        building_id=reading.building_id,
        timestamp=reading.timestamp,
        energy_kwh=reading.energy_kwh,
        meter_interval_minutes=reading.meter_interval_minutes,
        indoor_temp_c=reading.indoor_temp_c,
        outdoor_temp_c=reading.outdoor_temp_c,
        relative_humidity=reading.relative_humidity,
        occupancy_count=reading.occupancy_count,
        day_type=reading.day_type,
        operating_status=reading.operating_status,
        hvac_status=reading.hvac_status,
        tariff_rate=reading.tariff_rate,
        data_source=reading.data_source,
        is_synthetic=reading.is_synthetic,
        notes=reading.notes,
        created_at=reading.created_at,
        building_name=reading.building.name if reading.building else None,
        building_code=reading.building.code if reading.building else None,
    )


@router.get("/export/csv")
def export_csv(
    building_id: Optional[int] = Query(None, description="Optional building filter"),
    limit: int = Query(5000, le=20000, description="Max rows to export"),
    db: Session = Depends(get_db)
):
    """Export campus energy records as a downloadable CSV file."""
    csv_data = reading_service.export_readings_to_csv(db, building_id=building_id, limit=limit)
    filename = f"cit_energy_export_{get_utc_now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import/csv", response_model=CSVImportSummaryResponse)
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Bulk import energy observations from a CSV file."""
    content = await file.read()
    csv_text = content.decode("utf-8", errors="replace")
    return reading_service.import_readings_from_csv(db, csv_text)


@router.get("/{reading_id}", response_model=EnergyReadingResponse)
def get_reading(
    reading_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details of a single energy reading."""
    r = reading_service.get_energy_reading_by_id(db, reading_id)
    return EnergyReadingResponse(
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


@router.put("/{reading_id}", response_model=EnergyReadingResponse)
def update_reading(
    reading_id: int,
    data: EnergyReadingUpdate,
    db: Session = Depends(get_db)
):
    """Update fields of an existing energy observation."""
    r = reading_service.update_energy_reading(db, reading_id, data)
    return EnergyReadingResponse(
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


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(
    reading_id: int,
    db: Session = Depends(get_db)
):
    """Delete an energy observation."""
    reading_service.delete_energy_reading(db, reading_id)
    return None

