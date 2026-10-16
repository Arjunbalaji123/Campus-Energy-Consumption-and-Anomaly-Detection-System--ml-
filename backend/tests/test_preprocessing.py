"""Unit tests for Feature Engineering, Preprocessing, and Chronological Splitting."""
import os
import tempfile
import numpy as np
import pandas as pd
import pytest
from ml.preprocessing import (
    CampusEnergyPreprocessor,
    chronological_train_test_split,
    chronological_train_val_test_split,
    FEATURE_COLUMNS,
)
from ml.eda import run_eda, load_dataset


@pytest.fixture
def sample_raw_dataframe():
    """Create a sample dataframe of hourly readings for testing."""
    timestamps = pd.date_range("2026-10-01", periods=100, freq="h")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "building_code": ["CIT-IT"] * 50 + ["CIT-ACAD"] * 50,
        "building_category": ["IT Block"] * 50 + ["Academic Block"] * 50,
        "floor_area_sqm": [8500.0] * 50 + [9200.0] * 50,
        "max_capacity": [1200] * 50 + [1800] * 50,
        "has_hvac": [True] * 50 + [False] * 50,
        "energy_kwh": np.random.uniform(20.0, 150.0, 100),
        "outdoor_temp_c": np.random.uniform(24.0, 36.0, 100),
        "relative_humidity": np.random.uniform(40.0, 80.0, 100),
        "occupancy_count": np.random.randint(0, 1000, 100),
        "day_type": ["working_day"] * 80 + ["weekend"] * 20,
        "operating_status": ["normal"] * 80 + ["closed"] * 20,
    })
    return df


def test_cyclical_encoding_properties(sample_raw_dataframe):
    """Verify sine and cosine cyclical transformations maintain trigonometric identity."""
    preprocessor = CampusEnergyPreprocessor()
    df_feat = preprocessor._engineer_features(sample_raw_dataframe)

    # Values must remain within [-1.0, 1.0]
    for col in ["hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "month_sin", "month_cos"]:
        assert (df_feat[col] >= -1.0 - 1e-6).all()
        assert (df_feat[col] <= 1.0 + 1e-6).all()

    # sin^2 + cos^2 == 1.0
    hour_trig_sum = df_feat["hour_sin"]**2 + df_feat["hour_cos"]**2
    np.testing.assert_allclose(hour_trig_sum, 1.0, atol=1e-5)


def test_chronological_train_test_split(sample_raw_dataframe):
    """Verify chronological split strictly guarantees no future data leakage."""
    train_df, test_df = chronological_train_test_split(sample_raw_dataframe, test_ratio=0.20)

    assert len(train_df) == 80
    assert len(test_df) == 20

    # Max train timestamp must be strictly strictly before min test timestamp
    assert train_df["timestamp"].max() < test_df["timestamp"].min()


def test_missing_context_handling():
    """Verify that observations with missing temperatures or occupancies are handled gracefully."""
    timestamps = pd.date_range("2026-10-01", periods=10, freq="h")
    df_missing = pd.DataFrame({
        "timestamp": timestamps,
        "building_code": ["CIT-IT"] * 10,
        "building_category": ["IT Block"] * 10,
        "floor_area_sqm": [8500.0] * 10,
        "max_capacity": [1200] * 10,
        "has_hvac": [True] * 10,
        "energy_kwh": [50.0] * 10,
        "outdoor_temp_c": [None] * 10,       # Completely missing
        "relative_humidity": [None] * 10,    # Completely missing
        "occupancy_count": [None] * 10,      # Completely missing
        "day_type": ["working_day"] * 10,
        "operating_status": ["normal"] * 10,
    })

    preprocessor = CampusEnergyPreprocessor()
    preprocessor.fit(df_missing)
    X = preprocessor.transform(df_missing)

    assert X.shape == (10, len(FEATURE_COLUMNS))
    assert not np.isnan(X).any()  # No NaNs in transformed output


def test_preprocessor_serialization(sample_raw_dataframe):
    """Verify preprocessor can be saved and reloaded via joblib with identical outputs."""
    preprocessor = CampusEnergyPreprocessor()
    preprocessor.fit(sample_raw_dataframe)
    X_orig = preprocessor.transform(sample_raw_dataframe)

    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        preprocessor.save(tmp_path)
        loaded = CampusEnergyPreprocessor.load(tmp_path)
        X_loaded = loaded.transform(sample_raw_dataframe)

        np.testing.assert_allclose(X_orig, X_loaded)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_eda_execution():
    """Verify EDA execution runs against dataset and returns valid metric dictionary."""
    summary = run_eda(save_summary=False)
    assert "dataset_metrics" in summary
    assert summary["dataset_metrics"]["total_records"] >= 6480
    assert "building_consumption_stats" in summary
    assert "correlations_with_energy_kwh" in summary
    assert len(summary["injected_anomalies_detected"]) >= 4


def test_chronological_train_val_test_split(sample_raw_dataframe):
    """Verify 3-way chronological split maintains strict timestamp ordering across partitions."""
    train_df, val_df, test_df = chronological_train_val_test_split(
        sample_raw_dataframe, train_ratio=0.70, val_ratio=0.10, test_ratio=0.20
    )

    assert len(train_df) == 70
    assert len(val_df) == 10
    assert len(test_df) == 20

    # Ensure no future-data leakage
    assert train_df["timestamp"].max() < val_df["timestamp"].min()
    assert val_df["timestamp"].max() < test_df["timestamp"].min()


def test_evaluation_metrics_and_prediction_files_exist():
    """Verify that metrics.json and test_predictions.csv exist with valid structures."""
    import json
    from app.core.config import settings

    model_dir = os.path.abspath(settings.MODEL_DIR)
    metrics_path = os.path.join(model_dir, "metrics.json")
    pred_path = os.path.join(model_dir, "test_predictions.csv")

    assert os.path.exists(metrics_path), "metrics.json does not exist"
    assert os.path.exists(pred_path), "test_predictions.csv does not exist"

    with open(metrics_path, "r") as f:
        metrics = json.load(f)

    assert "random_forest" in metrics
    assert "lstm" in metrics
    assert "isolation_forest" in metrics
    assert metrics["random_forest"]["test_metrics"]["r2_score"] > 0.85
    assert metrics["lstm"]["test_metrics"]["r2_score"] > 0.85

    df_preds = pd.read_csv(pred_path)
    assert len(df_preds) == 1296
    expected_cols = {
        "timestamp", "building_code", "actual_energy_kwh", "rf_predicted_kwh",
        "rf_residual_kwh", "iso_forest_score", "iso_forest_is_outlier"
    }
    assert expected_cols.issubset(set(df_preds.columns))


