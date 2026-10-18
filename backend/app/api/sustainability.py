"""FastAPI REST endpoints for Campus Sustainability Intelligence Module."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.sustainability import (
    SustainabilitySummaryResponse, BuildingSustainabilityItem,
    SustainabilityTrendsResponse, CarbonFootprintResponse,
    EmissionsFactorInfo, EmissionsFactorUpdate,
    SustainabilityTargetCreate, SustainabilityTargetResponse,
    SustainabilityVerificationCreate, SustainabilityVerificationResponse,
    SustainabilityReportResponse
)
from app.services import sustainability_service

router = APIRouter(prefix="/sustainability", tags=["Sustainability Intelligence"])


@router.get("/summary", response_model=SustainabilitySummaryResponse)
def get_sustainability_summary(
    start_date: Optional[datetime] = Query(None, description="Start timestamp filter (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End timestamp filter (ISO 8601)"),
    building_id: Optional[int] = Query(None, description="Optional facility filter"),
    db: Session = Depends(get_db)
):
    """Retrieve campus-level and building-specific sustainability summary KPIs."""
    return sustainability_service.calculate_sustainability_summary(
        db, start_date=start_date, end_date=end_date, building_id=building_id
    )


@router.get("/buildings", response_model=List[BuildingSustainabilityItem])
def get_building_sustainability(
    start_date: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_date: Optional[datetime] = Query(None, description="End timestamp filter"),
    db: Session = Depends(get_db)
):
    """Retrieve normalized energy intensity (kWh/m²), carbon emissions, and baseline comparisons across facilities."""
    return sustainability_service.get_building_sustainability_rankings(
        db, start_date=start_date, end_date=end_date
    )


@router.get("/trends", response_model=SustainabilityTrendsResponse)
def get_sustainability_trends(
    building_id: Optional[int] = Query(None, description="Target building ID"),
    start_date: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_date: Optional[datetime] = Query(None, description="End timestamp filter"),
    granularity: str = Query("daily", pattern="^(daily|hourly)$", description="Timeseries aggregation granularity"),
    db: Session = Depends(get_db)
):
    """Retrieve chronological sustainability timeseries (actual kWh, baseline, emissions, intensity)."""
    return sustainability_service.get_sustainability_trends(
        db, building_id=building_id, start_date=start_date, end_date=end_date, granularity=granularity
    )


@router.get("/emissions", response_model=CarbonFootprintResponse)
def get_carbon_footprint(
    start_date: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_date: Optional[datetime] = Query(None, description="End timestamp filter"),
    db: Session = Depends(get_db)
):
    """Retrieve Scope 2 electricity carbon emissions breakdown and environmental equivalencies."""
    return sustainability_service.get_carbon_footprint_analysis(
        db, start_date=start_date, end_date=end_date
    )


@router.get("/factor", response_model=EmissionsFactorInfo)
def get_grid_emission_factor(db: Session = Depends(get_db)):
    """Retrieve active grid emission factor configuration and provenance."""
    return sustainability_service.get_emissions_factor_info(db)


@router.put("/factor", response_model=EmissionsFactorInfo)
def update_grid_emission_factor(
    update_data: EmissionsFactorUpdate,
    db: Session = Depends(get_db)
):
    """Configure regional grid emission factor (e.g. CEA India updates)."""
    return sustainability_service.update_emissions_factor(db, update_data)


@router.get("/targets", response_model=List[SustainabilityTargetResponse])
def get_sustainability_targets(db: Session = Depends(get_db)):
    """Retrieve institutional decarbonization targets with live progress tracking."""
    return sustainability_service.get_sustainability_targets(db)


@router.post("/targets", response_model=SustainabilityTargetResponse, status_code=status.HTTP_201_CREATED)
def create_sustainability_target(
    target_in: SustainabilityTargetCreate,
    db: Session = Depends(get_db)
):
    """Create a new campus decarbonization or energy efficiency target."""
    return sustainability_service.create_sustainability_target(db, target_in)


@router.get("/verification", response_model=List[SustainabilityVerificationResponse])
def get_verifications_ledger(db: Session = Depends(get_db)):
    """Retrieve empirical savings verification audit ledger."""
    return sustainability_service.get_verifications_ledger(db)


@router.post("/verify/{recommendation_id}", response_model=SustainabilityVerificationResponse)
def verify_recommendation_impact(
    recommendation_id: int = Path(..., description="Target recommendation ID to audit"),
    data: Optional[SustainabilityVerificationCreate] = None,
    db: Session = Depends(get_db)
):
    """Empirically audit post-action meter readings against baseline period to verify savings."""
    return sustainability_service.verify_recommendation_savings(db, recommendation_id, data)


@router.get("/report", response_model=SustainabilityReportResponse)
def get_sustainability_report(
    start_date: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_date: Optional[datetime] = Query(None, description="End timestamp filter"),
    db: Session = Depends(get_db)
):
    """Generate consolidated institutional sustainability audit report."""
    return sustainability_service.generate_sustainability_report(
        db, start_date=start_date, end_date=end_date
    )
