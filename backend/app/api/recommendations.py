"""FastAPI router for Practical Campus Recommendations and Investigation Workflows."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.recommendation import (
    RecommendationResponse, RecommendationStatusUpdateRequest,
    PaginatedRecommendationsResponse
)
from app.services import recommendation_engine

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=PaginatedRecommendationsResponse)
def list_recommendations(
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    priority: Optional[str] = Query(None, description="Filter: 'low', 'medium', 'high', 'critical'"),
    status: Optional[str] = Query(None, description="Filter: 'open', 'investigating', 'resolved', 'dismissed'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve actionable recommendations with transparent savings estimates and workflow status."""
    total, items = recommendation_engine.get_recommendations_paginated(
        db,
        building_id=building_id,
        priority=priority,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedRecommendationsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get("/{rec_id}", response_model=RecommendationResponse)
def get_recommendation(
    rec_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details of a specific recommendation."""
    r = recommendation_engine.get_recommendation_by_id(db, rec_id)
    event = r.anomaly_event
    reading = event.reading if event else None
    building = reading.building if reading else None

    return RecommendationResponse(
        id=r.id,
        anomaly_event_id=r.anomaly_event_id,
        title=r.title,
        priority=r.priority,
        supporting_evidence=r.supporting_evidence,
        recommended_action=r.recommended_action,
        responsible_role=r.responsible_role,
        follow_up_verification=r.follow_up_verification,
        status=r.status,
        estimated_savings_kwh=r.estimated_savings_kwh,
        building_name=building.name if building else "Unknown",
        building_code=building.code if building else "N/A",
        created_at=r.created_at,
    )


@router.put("/{rec_id}/status", response_model=RecommendationResponse)
def update_recommendation_status(
    rec_id: int,
    body: RecommendationStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update investigation and resolution status of a recommendation."""
    r = recommendation_engine.update_recommendation_status(db, rec_id, body.status)
    event = r.anomaly_event
    reading = event.reading if event else None
    building = reading.building if reading else None

    return RecommendationResponse(
        id=r.id,
        anomaly_event_id=r.anomaly_event_id,
        title=r.title,
        priority=r.priority,
        supporting_evidence=r.supporting_evidence,
        recommended_action=r.recommended_action,
        responsible_role=r.responsible_role,
        follow_up_verification=r.follow_up_verification,
        status=r.status,
        estimated_savings_kwh=r.estimated_savings_kwh,
        building_name=building.name if building else "Unknown",
        building_code=building.code if building else "N/A",
        created_at=r.created_at,
    )

