"""FastAPI router for Dashboard Overview and Campus Analytics."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dashboard import DashboardOverviewResponse, DashboardAnalyticsResponse
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    """Retrieve high-level campus energy KPIs, building breakdowns, and recent alerts."""
    return dashboard_service.get_dashboard_overview_metrics(db)


@router.get("/timeseries", response_model=DashboardAnalyticsResponse)
def get_timeseries_analytics(
    building_id: Optional[int] = Query(None, description="Optional building ID filter"),
    limit: int = Query(168, ge=24, le=720, description="Number of recent hourly data points to retrieve"),
    db: Session = Depends(get_db),
):
    """Retrieve chronological actual vs expected energy consumption time series and 24h diurnal profiles."""
    return dashboard_service.get_dashboard_timeseries_analytics(db, building_id=building_id, limit=limit)
