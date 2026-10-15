"""Service layer implementing Expected Energy Inference, Residual Analysis, and Model Tracking."""
import os
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import joblib
import pandas as pd
from app.core.config import settings
from app.models.building import Building
from app.models.reading import EnergyReading
from app.models.ml import ModelVersion, Prediction, ModelEvaluationRun
from app.schemas.prediction import PredictionResponse
from ml.preprocessing import CampusEnergyPreprocessor

# In-memory model cache to avoid repeated disk reads
_MODEL_CACHE = {}


def load_active_rf_model_and_preprocessor():
    """Load and cache the active Random Forest model and preprocessor."""
    if "rf" in _MODEL_CACHE and "preprocessor" in _MODEL_CACHE:
        return _MODEL_CACHE["rf"], _MODEL_CACHE["preprocessor"]

    model_dir = os.path.abspath(settings.MODEL_DIR)
    model_path = os.path.join(model_dir, "rf_expected_v1.joblib")
    prep_path = os.path.join(model_dir, "preprocessor.joblib")

    if not os.path.exists(model_path) or not os.path.exists(prep_path):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Active Random Forest model artifact is not yet trained or found on disk."
        )

    rf_model = joblib.load(model_path)
    preprocessor = CampusEnergyPreprocessor.load(prep_path)

    _MODEL_CACHE["rf"] = rf_model
    _MODEL_CACHE["preprocessor"] = preprocessor
    return rf_model, preprocessor


def generate_prediction_for_reading(db: Session, reading_id: int) -> Prediction:
    """Run real-time inference on an energy reading and store the expected prediction & residual."""
    reading = db.query(EnergyReading).filter(EnergyReading.id == reading_id).first()
    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Energy reading ID {reading_id} not found."
        )

    building = db.query(Building).filter(Building.id == reading.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building associated with reading not found.")

    rf_model, preprocessor = load_active_rf_model_and_preprocessor()

    # Get active model record from DB
    model_version = (
        db.query(ModelVersion)
        .filter(ModelVersion.version_tag == "rf_expected_v1")
        .first()
    )

    # Format observation dictionary matching preprocessor expectations
    obs = {
        "timestamp": reading.timestamp,
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

    X_sample = preprocessor.transform_single(obs)
    predicted_val = max(1.0, float(rf_model.predict(X_sample)[0]))
    actual_val = float(reading.energy_kwh)
    residual = actual_val - predicted_val

    # Safe percentage deviation (guard against division by near-zero)
    deviation_pct = (residual / predicted_val) * 100.0 if predicted_val > 0.1 else None

    # Check if a prediction already exists for this reading and model
    existing_pred = (
        db.query(Prediction)
        .filter(
            Prediction.reading_id == reading.id,
            Prediction.model_version_id == (model_version.id if model_version else None)
        )
        .first()
    )

    if existing_pred:
        existing_pred.predicted_energy_kwh = round(predicted_val, 2)
        existing_pred.residual_kwh = round(residual, 2)
        existing_pred.deviation_pct = round(deviation_pct, 2) if deviation_pct is not None else None
        pred_record = existing_pred
    else:
        pred_record = Prediction(
            reading_id=reading.id,
            building_id=building.id,
            model_version_id=model_version.id if model_version else None,
            predicted_energy_kwh=round(predicted_val, 2),
            residual_kwh=round(residual, 2),
            deviation_pct=round(deviation_pct, 2) if deviation_pct is not None else None,
        )
        db.add(pred_record)

    db.commit()
    db.refresh(pred_record)
    return pred_record


def get_predictions_paginated(
    db: Session,
    building_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 25
) -> Tuple[int, List[PredictionResponse]]:
    """Retrieve predictions with actual vs expected numbers and building enrichment."""
    query = (
        db.query(Prediction)
        .join(EnergyReading, Prediction.reading_id == EnergyReading.id)
        .join(Building, Prediction.building_id == Building.id)
    )

    if building_id:
        query = query.filter(Prediction.building_id == building_id)

    total = query.count()
    offset = (page - 1) * page_size
    records = (
        query.order_by(EnergyReading.timestamp.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for p in records:
        items.append(PredictionResponse(
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
        ))

    return total, items


def get_model_versions(db: Session) -> List[ModelVersion]:
    """Retrieve all registered ML model versions and their evaluation history."""
    return db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).all()


def get_evaluation_runs(db: Session, model_id: Optional[int] = None) -> List[ModelEvaluationRun]:
    """Retrieve benchmark runs with MAE, RMSE, and R2 scores."""
    query = db.query(ModelEvaluationRun)
    if model_id:
        query = query.filter(ModelEvaluationRun.model_version_id == model_id)
    return query.order_by(ModelEvaluationRun.created_at.desc()).all()

