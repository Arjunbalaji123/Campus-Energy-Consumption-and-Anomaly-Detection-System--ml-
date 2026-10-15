"""FastAPI router for Expected Energy Predictions and Residuals."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.prediction import PredictionResponse, PaginatedPredictionsResponse
from app.services import prediction_service

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("", response_model=PaginatedPredictionsResponse)
def list_predictions(
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated expected energy inferences vs actual consumption."""
    total, items = prediction_service.get_predictions_paginated(
        db,
        building_id=building_id,
        page=page,
        page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedPredictionsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.post("/generate/{reading_id}", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
def generate_prediction(
    reading_id: int,
    db: Session = Depends(get_db)
):
    """Run real-time Random Forest inference on an energy reading to compute expected kWh and residual."""
    p = prediction_service.generate_prediction_for_reading(db, reading_id)
    return PredictionResponse(
        id=p.id,
        reading_id=p.reading_id,
        building_id=p.building_id,
        building_name=p.building.name if p.building else None,
        building_code=p.building.code if p.building else None,
        timestamp=p.reading.timestamp if p.reading else None,
        actual_energy_kwh=p.reading.energy_kwh if p.reading else None,
        predicted_energy_kwh=p.predicted_energy_kwh,
        residual_kwh=p.residual_kwh,
        deviation_pct=p.deviation_pct,
        model_version_tag=p.model_version.version_tag if p.model_version else None,
        created_at=p.created_at,
    )

