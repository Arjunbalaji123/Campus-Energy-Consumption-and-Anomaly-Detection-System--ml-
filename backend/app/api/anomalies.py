"""FastAPI router for Anomaly Events, Detection Runs, and Investigation Status."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.anomaly import (
    AnomalyEventResponse, AnomalyStatusUpdateRequest,
    PaginatedAnomaliesResponse, AnomalyScanSummaryResponse
)
from app.services import anomaly_service

router = APIRouter(prefix="/anomalies", tags=["Anomaly Center"])


def _build_anomaly_response(a) -> AnomalyEventResponse:
    r = a.reading
    p = a.prediction
    b = r.building if r else None
    return AnomalyEventResponse(
        id=a.id,
        reading_id=a.reading_id,
        prediction_id=a.prediction_id,
        building_id=b.id if b else 0,
        building_name=b.name if b else "Unknown",
        building_code=b.code if b else "N/A",
        timestamp=r.timestamp if r else a.detected_at,
        actual_energy_kwh=r.energy_kwh if r else 0.0,
        predicted_energy_kwh=p.predicted_energy_kwh if p else None,
        residual_kwh=p.residual_kwh if p else None,
        deviation_pct=p.deviation_pct if p else None,
        detection_method=a.detection_method,
        severity=a.severity,
        anomaly_score=a.anomaly_score,
        status=a.status,
        detected_at=a.detected_at,
        indoor_temp_c=r.indoor_temp_c if r else None,
        outdoor_temp_c=r.outdoor_temp_c if r else None,
        relative_humidity=r.relative_humidity if r else None,
        occupancy_count=r.occupancy_count if r else None,
        max_capacity=b.max_capacity if b else None,
        day_type=r.day_type if r else None,
        operating_status=r.operating_status if r else None,
        hvac_status=r.hvac_status if r else None,
        floor_area_sqm=b.floor_area_sqm if b else None,
        explanations=a.explanations or [],
        recommendations=a.recommendations or [],
    )


@router.get("", response_model=PaginatedAnomaliesResponse)
def list_anomalies(
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    severity: Optional[str] = Query(None, description="Filter: 'warning', 'critical'"),
    status: Optional[str] = Query(None, description="Filter: 'open', 'investigating', 'resolved', 'dismissed'"),
    method: Optional[str] = Query(None, description="Filter: 'residual', 'isolation_forest', 'dual'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List detected anomalies with contextual filtering and pagination."""
    total, items = anomaly_service.get_anomalies_paginated(
        db,
        building_id=building_id,
        severity=severity,
        status_filter=status,
        method=method,
        page=page,
        page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedAnomaliesResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/{anomaly_id}", response_model=AnomalyEventResponse)
def get_anomaly_details(
    anomaly_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details, forensic context, explanations, and recommendations for a specific anomaly event."""
    a = anomaly_service.get_anomaly_by_id(db, anomaly_id)
    return _build_anomaly_response(a)


@router.put("/{anomaly_id}/status", response_model=AnomalyEventResponse)
def update_status(
    anomaly_id: int,
    body: AnomalyStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update workflow status of an anomaly ('open', 'investigating', 'resolved', 'dismissed')."""
    a = anomaly_service.update_anomaly_status(db, anomaly_id, body.status)
    return _build_anomaly_response(a)


@router.post("/detect/{reading_id}", response_model=Optional[AnomalyEventResponse])
def run_detection(
    reading_id: int,
    db: Session = Depends(get_db)
):
    """Run dual-method anomaly detection on a single reading and persist result."""
    a = anomaly_service.evaluate_reading_anomalies(db, reading_id)
    if not a:
        return None
    return _build_anomaly_response(a)


@router.post("/batch-scan", response_model=AnomalyScanSummaryResponse)
def batch_scan(
    limit: int = Query(2000, le=10000, description="Max observations to scan"),
    db: Session = Depends(get_db)
):
    """Scan campus observations and populate the Anomaly Center."""
    res = anomaly_service.batch_scan_energy_readings(db, limit=limit)
    return AnomalyScanSummaryResponse(**res)
