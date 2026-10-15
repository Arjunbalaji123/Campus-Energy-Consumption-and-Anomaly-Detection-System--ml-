"""Integration and Unit Tests for Random Forest Expected Energy Prediction and APIs."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import ModelVersion, ModelEvaluationRun, EnergyReading, Prediction
from app.services.prediction_service import (
    load_active_rf_model_and_preprocessor,
    generate_prediction_for_reading
)

client = TestClient(app)


def test_model_artifacts_exist_and_loadable():
    """Verify saved Random Forest model and preprocessor artifacts exist on disk."""
    model_dir = os.path.abspath(settings.MODEL_DIR)
    model_path = os.path.join(model_dir, "rf_expected_v1.joblib")
    prep_path = os.path.join(model_dir, "preprocessor.joblib")

    assert os.path.exists(model_path)
    assert os.path.exists(prep_path)

    rf, prep = load_active_rf_model_and_preprocessor()
    assert rf is not None
    assert prep is not None
    assert prep.is_fitted is True


def test_model_registered_in_database():
    """Verify model version and evaluation benchmarks are saved in the database."""
    db = SessionLocal()
    try:
        mv = db.query(ModelVersion).filter(ModelVersion.version_tag == "rf_expected_v1").first()
        assert mv is not None
        assert mv.algorithm == "RandomForestRegressor"
        assert mv.is_active is True
        assert "test" in mv.metrics
        assert mv.metrics["test"]["r2"] > 0.85 # Strong performance on test data

        eval_run = db.query(ModelEvaluationRun).filter(ModelEvaluationRun.model_version_id == mv.id).first()
        assert eval_run is not None
        assert eval_run.sample_count > 0
        assert eval_run.r2_score > 0.85
        assert eval_run.mae > 0.0
        assert eval_run.rmse > 0.0
    finally:
        db.close()


def test_realtime_prediction_service():
    """Verify real-time inference on a single reading computes expected kWh and residual."""
    db = SessionLocal()
    try:
        sample_reading = db.query(EnergyReading).first()
        pred = generate_prediction_for_reading(db, sample_reading.id)

        assert pred is not None
        assert pred.predicted_energy_kwh > 0.0
        assert pred.residual_kwh == pytest.approx(sample_reading.energy_kwh - pred.predicted_energy_kwh, 0.05)
        if pred.predicted_energy_kwh > 0.1:
            assert pred.deviation_pct is not None
    finally:
        db.close()


def test_list_predictions_api():
    """Verify GET /api/predictions endpoint returns enriched predictions."""
    response = client.get("/api/predictions?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert data["total"] > 0
    assert len(data["items"]) == 10

    item = data["items"][0]
    assert "predicted_energy_kwh" in item
    assert "actual_energy_kwh" in item
    assert "residual_kwh" in item
    assert "building_name" in item


def test_generate_prediction_api():
    """Verify POST /api/predictions/generate/{id} generates inference via HTTP."""
    db = SessionLocal()
    try:
        reading = db.query(EnergyReading).order_by(EnergyReading.id.desc()).first()
        reading_id = reading.id
    finally:
        db.close()

    response = client.post(f"/api/predictions/generate/{reading_id}")
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["reading_id"] == reading_id
    assert data["predicted_energy_kwh"] > 0.0


def test_models_and_evaluations_api():
    """Verify GET /api/models and /api/models/evaluations."""
    m_res = client.get("/api/models")
    assert m_res.status_code == 200
    models = m_res.json()
    tags = {m["version_tag"] for m in models}
    assert "rf_expected_v1" in tags

    e_res = client.get("/api/models/evaluations")
    assert e_res.status_code == 200
    evals = e_res.json()
    assert len(evals) >= 1
    assert evals[0]["r2_score"] > 0.85

