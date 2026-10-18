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
    SustainabilityReportResponse,
    EnergyWasteEventItem, WhatIfScenarioRequest, WhatIfScenarioResponse
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
@router.get("/settings", response_model=EmissionsFactorInfo)
def get_grid_emission_factor(db: Session = Depends(get_db)):
    """Retrieve active grid emission factor configuration and provenance."""
    return sustainability_service.get_emissions_factor_info(db)


@router.put("/factor", response_model=EmissionsFactorInfo)
@router.put("/settings", response_model=EmissionsFactorInfo)
def update_grid_emission_factor(
    update_data: EmissionsFactorUpdate,
    db: Session = Depends(get_db)
):
    """Configure regional grid emission factor (e.g. CEA India updates)."""
    return sustainability_service.update_emissions_factor(db, update_data)


@router.get("/recommendations")
def get_sustainability_recommendations(
    building_id: Optional[int] = Query(None, description="Optional facility filter"),
    db: Session = Depends(get_db)
):
    """Retrieve actionable sustainability and energy-efficiency directives."""
    from app.models.anomaly import Recommendation, AnomalyEvent
    from app.models.reading import EnergyReading
    q = db.query(Recommendation).join(AnomalyEvent, Recommendation.anomaly_event_id == AnomalyEvent.id).join(EnergyReading, AnomalyEvent.reading_id == EnergyReading.id)
    if building_id:
        q = q.filter(EnergyReading.building_id == building_id)
    recs = q.order_by(Recommendation.id.desc()).limit(50).all()
    results = []
    for r in recs:
        results.append({
            "id": r.id,
            "anomaly_event_id": r.anomaly_event_id,
            "title": r.title,
            "priority": r.priority,
            "supporting_evidence": r.supporting_evidence,
            "recommended_action": r.recommended_action,
            "responsible_role": r.responsible_role,
            "follow_up_verification": r.follow_up_verification,
            "status": r.status,
            "estimated_savings_kwh": r.estimated_savings_kwh,
            "estimated_cost_reduction_inr": round((r.estimated_savings_kwh or 0.0) * 7.50, 2),
            "estimated_emissions_reduction_kg_co2e": round((r.estimated_savings_kwh or 0.0) * 0.716, 2),
            "created_at": r.created_at,
        })
    return results


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


@router.get("/waste-events", response_model=List[EnergyWasteEventItem])
def get_energy_waste_events(
    building_id: Optional[int] = Query(None, description="Optional facility filter"),
    limit: int = Query(50, le=200, description="Max observations"),
    db: Session = Depends(get_db)
):
    """Detect and classify avoidable energy waste events from off-hours surges and excessive baseload."""
    return sustainability_service.get_energy_waste_events(db, building_id=building_id, limit=limit)


@router.post("/scenarios/what-if", response_model=WhatIfScenarioResponse)
def run_what_if_scenario(
    request: WhatIfScenarioRequest,
    db: Session = Depends(get_db)
):
    """Execute physics-based hypothetical efficiency and solar PV decarbonization simulation."""
    return sustainability_service.simulate_what_if_scenario(db, request)

