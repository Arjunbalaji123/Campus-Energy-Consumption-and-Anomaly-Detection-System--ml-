"""Actionable Recommendation Engine for CIT Campus Energy Anomaly Management.

Generates practical, role-assigned corrective tasks with transparent savings estimates
and audit verification steps.
"""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.building import Building
from app.models.reading import EnergyReading
from app.models.ml import Prediction
from app.models.anomaly import AnomalyEvent, AnomalyExplanation, Recommendation
from app.schemas.recommendation import RecommendationResponse


def generate_recommendation_for_anomaly(
    building: Building,
    reading: EnergyReading,
    prediction: Prediction,
    anomaly: AnomalyEvent,
    explanation_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate practical recommendation based on observed evidence and rule hypothesis.
    
    Returns a dictionary of fields for creating a Recommendation record.
    """
    actual_kwh = float(reading.energy_kwh)
    pred_kwh = float(prediction.predicted_energy_kwh) if prediction else 0.0
    residual = float(prediction.residual_kwh) if prediction else 0.0
    interval_hours = float(reading.meter_interval_minutes or 60) / 60.0
    tariff = float(reading.tariff_rate or 7.50)

    # Documented saving estimate: bringing consumption back to expected baseline
    estimated_kwh_savings = max(0.0, round(residual * interval_hours, 2)) if residual > 0 else 0.0
    estimated_inr_savings = round(estimated_kwh_savings * tariff, 2)

    hypothesis = explanation_data.get("primary_hypothesis", "")
    evidence = explanation_data.get("evidence", {})
    confidence = explanation_data.get("confidence", "medium")

    # CASE 1: Critical Off-Hours / Low Occupancy Heavy Load
    if "outside standard operating hours" in hypothesis or "minimal occupant presence" in hypothesis:
        return {
            "title": f"Investigate After-Hours Equipment / HVAC in {building.name}",
            "priority": "critical" if anomaly.severity == "critical" else "high",
            "supporting_evidence": (
                f"Reading was {actual_kwh} kWh vs expected {pred_kwh} kWh (+{residual:.1f} kWh) "
                f"during off-hours with only {reading.occupancy_count or 0} occupants recorded."
            ),
            "recommended_action": (
                f"1. Dispatch security/facilities staff to inspect {building.name} floor by floor.\n"
                f"2. Manually power off inactive split ACs, laboratory computers, and decorative lighting.\n"
                f"3. Verify centralized BMS time-clock schedules to ensure automated shutdown at closing hours."
            ),
            "responsible_role": "Facilities Staff",
            "follow_up_verification": (
                f"Verify subsequent hourly meter readings return below standby threshold "
                f"({pred_kwh:.1f} kWh). Estimated avoidable waste: ~{estimated_kwh_savings} kWh (₹{estimated_inr_savings})."
            ),
            "estimated_savings_kwh": estimated_kwh_savings,
        }

    # CASE 2: Severe Drop / Meter Failure / Breaker Trip
    elif "low energy consumption" in hypothesis or "breaker trip" in hypothesis:
        return {
            "title": f"Emergency Electrical & Meter Inspection in {building.name}",
            "priority": "critical",
            "supporting_evidence": (
                f"Consumption plunged to {actual_kwh} kWh during normal operational hours "
                f"(expected {pred_kwh} kWh). Indicates zero/near-zero load on active building."
            ),
            "recommended_action": (
                f"1. Check status of main Air Circuit Breaker (ACB) or Molded Case Circuit Breaker (MCCB) at main switchboard.\n"
                f"2. Inspect smart energy meter communication cable and current transformers (CTs) for loose terminals.\n"
                f"3. Verify if an unscheduled building power outage occurred."
            ),
            "responsible_role": "Electrical Engineer",
            "follow_up_verification": "Ensure meter resumes recording expected load (> 50 kWh) once power/telemetry is restored.",
            "estimated_savings_kwh": 0.0,
        }

    # CASE 3: Thermal Surge / High Ambient Cooling Demand
    elif "ambient outdoor temperature" in hypothesis or "chiller plant" in hypothesis:
        return {
            "title": f"Optimize HVAC Setpoints & Chiller Efficiency in {building.name}",
            "priority": "high",
            "supporting_evidence": (
                f"Outdoor temperature reached {reading.outdoor_temp_c}°C, causing excess consumption "
                f"of {residual:.1f} kWh above expected baseline."
            ),
            "recommended_action": (
                f"1. Adjust thermostat setpoints from 21°C-22°C to energy-efficient 24°C-25°C.\n"
                f"2. Clean air filters on fan coil units and verify condenser cooling tower water flow.\n"
                f"3. Ensure windows and exterior doors are kept closed while air conditioning operates."
            ),
            "responsible_role": "Energy Manager",
            "follow_up_verification": f"Measure reduction in chiller peak demand during next peak heat cycle. Potential saving: ~{estimated_kwh_savings} kWh (₹{estimated_inr_savings}).",
            "estimated_savings_kwh": estimated_kwh_savings,
        }

    # CASE 4: Daytime In-Hours High Load
    elif "normal occupancy" in hypothesis:
        return {
            "title": f"Sub-Circuit Energy Audit for Departmental Labs in {building.name}",
            "priority": "medium",
            "supporting_evidence": (
                f"Unexpected {residual:.1f} kWh excess during daytime operations. Normal occupancy ({reading.occupancy_count} occupants)."
            ),
            "recommended_action": (
                f"1. Review scheduled laboratory sessions and workshop trials conducted during this window.\n"
                f"2. Check whether heavy inductive machines or server lab test benches were left idling between practicals."
            ),
            "responsible_role": "Lab Technician",
            "follow_up_verification": "Compare against previous week's identical timetable period.",
            "estimated_savings_kwh": estimated_kwh_savings,
        }

    # CASE 5: General / Insufficient Context
    return {
        "title": f"General Energy Walk-Through Inspection in {building.name}",
        "priority": "low",
        "supporting_evidence": f"Anomaly detected by statistical model with deviation of {residual:+.1f} kWh.",
        "recommended_action": "Conduct a walkthrough inspection to identify unrecorded loads and ensure equipment is properly turned off.",
        "responsible_role": "Facilities Staff",
        "follow_up_verification": "Re-check energy dashboard over the next 24 hours.",
        "estimated_savings_kwh": estimated_kwh_savings,
    }


def get_recommendations_paginated(
    db: Session,
    building_id: Optional[int] = None,
    priority: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 25
) -> Tuple[int, List[RecommendationResponse]]:
    """Retrieve paginated recommendations with building enrichment."""
    query = (
        db.query(Recommendation)
        .join(AnomalyEvent, Recommendation.anomaly_event_id == AnomalyEvent.id)
        .join(EnergyReading, AnomalyEvent.reading_id == EnergyReading.id)
        .join(Building, EnergyReading.building_id == Building.id)
    )

    if building_id:
        query = query.filter(EnergyReading.building_id == building_id)
    if priority:
        query = query.filter(Recommendation.priority == priority)
    if status_filter:
        query = query.filter(Recommendation.status == status_filter)

    total = query.count()
    offset = (page - 1) * page_size
    records = query.order_by(Recommendation.created_at.desc()).offset(offset).limit(page_size).all()

    items = []
    for r in records:
        event = r.anomaly_event
        reading = event.reading if event else None
        building = reading.building if reading else None

        items.append(RecommendationResponse(
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
        ))

    return total, items


def get_recommendation_by_id(db: Session, rec_id: int) -> Recommendation:
    """Retrieve a recommendation by ID or raise 404."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation ID {rec_id} not found.")
    return rec


def update_recommendation_status(db: Session, rec_id: int, new_status: str) -> Recommendation:
    """Update workflow status of a recommendation ('open', 'investigating', 'resolved', 'dismissed')."""
    rec = get_recommendation_by_id(db, rec_id)
    rec.status = new_status
    db.commit()
    db.refresh(rec)
    return rec

