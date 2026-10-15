"""Tests for Deep Learning LSTM Model and Comparative Evaluation APIs."""
import os
import joblib
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from ml.lstm_model import CITLSTMRegressor

client = TestClient(app)


def test_lstm_forward_and_prediction():
    """Verify CITLSTMRegressor cell gate computations and output projection."""
    B, L, D, H = 8, 24, 8, 16
    model = CITLSTMRegressor(input_dim=D, hidden_dim=H, sequence_length=L, random_state=42)
    X = np.random.randn(B, L, D)
    
    y_pred, cache = model.forward(X)
    assert y_pred.shape == (B, 1)
    assert len(cache) == L
    assert "h" in cache[-1]
    assert "c" in cache[-1]
    
    # Test batch predict
    preds = model.predict(X, batch_size=4)
    assert preds.shape == (B, 1)


def test_lstm_artifact_saved_and_loadable():
    """Verify saved LSTM artifact bundle exists and contains weights and scalers."""
    artifact_path = os.path.join(os.path.dirname(__file__), "..", "ml", "saved_models", "lstm_expected_v1.joblib")
    assert os.path.exists(artifact_path)
    
    bundle = joblib.load(artifact_path)
    assert "model_weights" in bundle
    assert "scaler_x" in bundle
    assert "scaler_y" in bundle
    assert "metrics" in bundle
    assert bundle["metrics"]["r2"] > 0.85
    assert bundle["metrics"]["mae"] < 2.0


def test_models_comparison_endpoint():
    """Verify /api/models/comparison returns side-by-side benchmark comparison."""
    res = client.get("/api/models/comparison")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert len(data["models"]) == 2
    
    rf = next(m for m in data["models"] if m["version_tag"] == "rf_expected_v1")
    lstm = next(m for m in data["models"] if m["version_tag"] == "lstm_expected_v1")
    
    assert rf["metrics"]["r2"] >= 0.90
    assert lstm["metrics"]["r2"] >= 0.90
    assert "trade_off_analysis" in data
    assert len(data["trade_off_analysis"]["when_traditional_ml_is_preferred"]) > 0
    assert len(data["trade_off_analysis"]["when_deep_learning_is_justified"]) > 0

