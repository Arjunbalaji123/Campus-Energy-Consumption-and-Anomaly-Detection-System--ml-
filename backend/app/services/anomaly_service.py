"""Service layer implementing Dual-Method Anomaly Detection: Residual Analysis and Isolation Forest."""
import os
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import joblib
import numpy as np
import pandas as pd

from app.core.config import settings
from app.models.building import Building
from app.models.reading import EnergyReading
from app.models.ml import Prediction
from app.models.anomaly import AnomalyEvent
from app.schemas.anomaly import AnomalyEventResponse
from app.services.prediction_service import generate_prediction_for_reading, load_active_rf_model_and_preprocessor

_ISO_CACHE = {}


def load_active_isolation_detector():
    """Load and cache the trained Isolation Forest detector package."""
    if "iso" in _ISO_CACHE:
        return _ISO_CACHE["iso"]

    model_dir = os.path.abspath(settings.MODEL_DIR)
    iso_path = os.path.join(model_dir, "iso_forest_v1.joblib")

    if not os.path.exists(iso_path):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Isolation Forest model artifact is not yet trained or found on disk."
        )

    package = joblib.load(iso_path)
    _ISO_CACHE["iso"] = package
    return package


def evaluate_reading_anomalies(
    db: Session,
    reading_id: int,
    warning_threshold: float = None,
    critical_threshold: float = None
) -> Optional[AnomalyEvent]:
    """Run dual-method anomaly detection (Residual Analysis + Isolation Forest) on a reading."""
    warn_thresh = warning_threshold or settings.ANOMALY_WARNING_THRESHOLD
    crit_thresh = critical_threshold or settings.ANOMALY_CRITICAL_THRESHOLD

    reading = db.query(EnergyReading).filter(EnergyReading.id == reading_id).first()
    if not reading:
        raise HTTPException(status_code=404, detail=f"Reading ID {reading_id} not found.")

    building = db.query(Building).filter(Building.id == reading.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found.")

    # 1. Ensure Prediction exists or generate it
    prediction = (
        db.query(Prediction)
        .filter(Prediction.reading_id == reading.id)
        .first()
    )
    if not prediction:
        prediction = generate_prediction_for_reading(db, reading.id)

    actual_kwh = float(reading.energy_kwh)
    pred_kwh = float(prediction.predicted_energy_kwh)
    residual = float(prediction.residual_kwh)

    # 2. Method A: Residual Analysis
    # Safe relative deviation percentage: |Residual| / Predicted
    rel_dev = abs(residual) / pred_kwh if pred_kwh > 0.1 else 0.0

    residual_severity = "normal"
    if rel_dev >= crit_thresh:
        residual_severity = "critical"
    elif rel_dev >= warn_thresh:
        residual_severity = "warning"

    # 3. Method B: Isolation Forest Outlier Scoring
    iso_package = load_active_isolation_detector()
    iso_model = iso_package["model"]
    iso_scaler = iso_package["scaler"]
    iso_features = iso_package["features"]
    _, preprocessor = load_active_rf_model_and_preprocessor()

    obs = {
        "timestamp": reading.timestamp,
        "energy_kwh": actual_kwh,
        "building_code": building.code,
        "building_name": building.name,
        "building_category": building.category,
        "floor_area_sqm": building.floor_area_sqm,
        "max_capacity": building.max_capacity,
        "has_hvac": building.has_hvac,
        "outdoor_temp_c": reading.outdoor_temp_c,
        "relative_humidity": reading.relative_humidity,
        "occupancy_count": reading.occupancy_count,
        "day_type": reading.day_type,
        "operating_status": reading.operating_status,
    }

    df_obs = pd.DataFrame([obs])
    df_feat = preprocessor._engineer_features(df_obs)
    df_feat["kwh_per_sqm"] = df_feat["energy_kwh"] / df_feat["floor_area_sqm"].clip(lower=100.0)

    X_raw = df_feat[iso_features].values
    X_scaled = iso_scaler.transform(X_raw)

    iso_score = float(iso_model.decision_function(X_scaled)[0])
    is_iso_outlier = bool(iso_model.predict(X_scaled)[0] == -1)

    # 4. Synthesize Dual Anomaly Verdict
    is_res_anomaly = (residual_severity != "normal")

    if is_res_anomaly and is_iso_outlier:
        method = "dual"
        severity = "critical"
    elif is_res_anomaly:
        method = "residual"
        severity = residual_severity
    elif is_iso_outlier:
        method = "isolation_forest"
        severity = "warning"
    else:
        # Both methods agree observation is normal
        # Clean up any previously created anomaly event if updated reading became normal
        db.query(AnomalyEvent).filter(AnomalyEvent.reading_id == reading.id).delete()
        db.commit()
        return None

    # 5. Persist or update AnomalyEvent in DB
    existing_event = db.query(AnomalyEvent).filter(AnomalyEvent.reading_id == reading.id).first()
    if existing_event:
        existing_event.prediction_id = prediction.id
        existing_event.detection_method = method
        existing_event.severity = severity
        existing_event.anomaly_score = round(iso_score, 4)
        event = existing_event
    else:
        event = AnomalyEvent(
            reading_id=reading.id,
            prediction_id=prediction.id,
            detection_method=method,
            severity=severity,
            anomaly_score=round(iso_score, 4),
            status="open",
            detected_at=datetime.utcnow(),
        )
        db.add(event)

    db.commit()
    db.refresh(event)

    # 6. Generate evidence-based explanation and actionable recommendation
    from app.models.anomaly import AnomalyExplanation, Recommendation
    from app.services.explanation_engine import evaluate_anomaly_explanation
    from app.services.recommendation_engine import generate_recommendation_for_anomaly

    expl_data = evaluate_anomaly_explanation(building, reading, prediction, event)
    existing_expl = db.query(AnomalyExplanation).filter(AnomalyExplanation.anomaly_event_id == event.id).first()
    if existing_expl:
        existing_expl.primary_hypothesis = expl_data["primary_hypothesis"]
        existing_expl.evidence = expl_data["evidence"]
        existing_expl.confidence = expl_data["confidence"]
        existing_expl.data_to_confirm = expl_data["data_to_confirm"]
        existing_expl.recommended_next_action = expl_data["recommended_next_action"]
    else:
        expl = AnomalyExplanation(
            anomaly_event_id=event.id,
            primary_hypothesis=expl_data["primary_hypothesis"],
            evidence=expl_data["evidence"],
            confidence=expl_data["confidence"],
            data_to_confirm=expl_data["data_to_confirm"],
            recommended_next_action=expl_data["recommended_next_action"],
        )
        db.add(expl)

    rec_data = generate_recommendation_for_anomaly(building, reading, prediction, event, expl_data)
    existing_rec = db.query(Recommendation).filter(Recommendation.anomaly_event_id == event.id).first()
    if existing_rec:
        existing_rec.title = rec_data["title"]
        existing_rec.priority = rec_data["priority"]
        existing_rec.supporting_evidence = rec_data["supporting_evidence"]
        existing_rec.recommended_action = rec_data["recommended_action"]
        existing_rec.responsible_role = rec_data["responsible_role"]
        existing_rec.follow_up_verification = rec_data["follow_up_verification"]
        existing_rec.estimated_savings_kwh = rec_data["estimated_savings_kwh"]
    else:
        rec = Recommendation(
            anomaly_event_id=event.id,
            title=rec_data["title"],
            priority=rec_data["priority"],
            supporting_evidence=rec_data["supporting_evidence"],
            recommended_action=rec_data["recommended_action"],
            responsible_role=rec_data["responsible_role"],
            follow_up_verification=rec_data["follow_up_verification"],
            status="open",
            estimated_savings_kwh=rec_data["estimated_savings_kwh"],
        )
        db.add(rec)

    db.commit()
    db.refresh(event)
    return event


def batch_scan_energy_readings(
    db: Session,
    limit: int = 5000,
    warning_threshold: float = None,
    critical_threshold: float = None
) -> Dict[str, Any]:
    """Scan historical observations and generate anomaly events."""
    readings = db.query(EnergyReading.id).order_by(EnergyReading.timestamp.desc()).limit(limit).all()

    total = len(readings)
    anomalies = 0
    warnings = 0
    criticals = 0
    duals = 0

    for r in readings:
        event = evaluate_reading_anomalies(
            db,
            reading_id=r.id,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold
        )
        if event:
            anomalies += 1
            if event.severity == "critical":
                criticals += 1
            elif event.severity == "warning":
                warnings += 1
            if event.detection_method == "dual":
                duals += 1

    return {
        "total_scanned": total,
        "anomalies_detected": anomalies,
        "warning_count": warnings,
        "critical_count": criticals,
        "dual_count": duals,
        "message": f"Scanned {total} observations. Detected {anomalies} anomalies ({duals} confirmed by both methods)."
    }


def get_anomalies_paginated(
    db: Session,
    building_id: Optional[int] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    method: Optional[str] = None,
    page: int = 1,
    page_size: int = 25
) -> Tuple[int, List[AnomalyEventResponse]]:
    """Retrieve paginated anomaly events with reading and prediction context."""
    query = (
        db.query(AnomalyEvent)
        .join(EnergyReading, AnomalyEvent.reading_id == EnergyReading.id)
        .join(Building, EnergyReading.building_id == Building.id)
        .outerjoin(Prediction, AnomalyEvent.prediction_id == Prediction.id)
    )

    if building_id:
        query = query.filter(EnergyReading.building_id == building_id)
    if severity:
        query = query.filter(AnomalyEvent.severity == severity)
    if status_filter:
        query = query.filter(AnomalyEvent.status == status_filter)
    if method:
        query = query.filter(AnomalyEvent.detection_method == method)

    total = query.count()
    offset = (page - 1) * page_size
    records = query.order_by(EnergyReading.timestamp.desc()).offset(offset).limit(page_size).all()

    items = []
    for a in records:
        r = a.reading
        p = a.prediction
        b = r.building if r else None

        items.append(AnomalyEventResponse(
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
        ))

    return total, items


def get_anomaly_by_id(db: Session, anomaly_id: int) -> AnomalyEvent:
    """Retrieve an anomaly event by ID or raise 404."""
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Anomaly event ID {anomaly_id} not found.")
    return event


def update_anomaly_status(db: Session, anomaly_id: int, new_status: str) -> AnomalyEvent:
    """Update investigation status ('open', 'investigating', 'resolved', 'dismissed')."""
    event = get_anomaly_by_id(db, anomaly_id)
    event.status = new_status
    db.commit()
    db.refresh(event)
    return event
