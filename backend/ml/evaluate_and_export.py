"""Unified Evaluation and Test Prediction Exporter for CIT Energy System.

Strictly evaluates Random Forest, LSTM, and Isolation Forest models on the
held-out chronological test split (unseen future observations), writes comprehensive
performance benchmarks to `metrics.json`, and outputs observation-level test predictions
to `test_predictions.csv`.
"""
import os
import sys
import json
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from ml.eda import load_dataset
from ml.preprocessing import CampusEnergyPreprocessor, chronological_train_test_split
from ml.lstm_model import CITLSTMRegressor
from ml.train_lstm import _engineer_lstm_features, _build_sequences, SEQUENCE_FEATURES, SEQUENCE_LENGTH, PREDICTION_HORIZON
from ml.train_isolation_forest import prepare_isolation_features, ISOLATION_FEATURES


def evaluate_models_and_export_predictions() -> dict:
    """Run strict held-out evaluation across all 3 models and export metrics.json & test_predictions.csv."""
    print("=" * 75)
    print("CIT COIMBATORE - RIGOROUS HELD-OUT TEST EVALUATION & PREDICTION EXPORT")
    print("=" * 75)

    # 1. Load Dataset
    df = load_dataset(synthetic_only=True)
    total_records = len(df)
    print(f"Loaded {total_records} total reproducible synthetic campus observations.")

    # 2. Chronological Split (Strict 80:20 Partition)
    train_df, test_df = chronological_train_test_split(df, test_ratio=0.20)
    train_start, train_end = train_df["timestamp"].min(), train_df["timestamp"].max()
    test_start, test_end = test_df["timestamp"].min(), test_df["timestamp"].max()

    print(f"Train partition : {len(train_df)} rows ({train_start.strftime('%Y-%m-%d %H:%M')} to {train_end.strftime('%Y-%m-%d %H:%M')})")
    print(f"Test partition  : {len(test_df)} rows ({test_start.strftime('%Y-%m-%d %H:%M')} to {test_end.strftime('%Y-%m-%d %H:%M')})")
    print("-" * 75)

    # 3. Load Saved Artifacts
    model_dir = os.path.abspath(settings.MODEL_DIR)
    rf_path = os.path.join(model_dir, "rf_expected_v1.joblib")
    prep_path = os.path.join(model_dir, "preprocessor.joblib")
    iso_path = os.path.join(model_dir, "iso_forest_v1.joblib")
    lstm_path = os.path.join(model_dir, "lstm_expected_v1.joblib")

    for path in [rf_path, prep_path, iso_path, lstm_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required model artifact: {path}. Run training scripts first.")

    rf_model = joblib.load(rf_path)
    preprocessor = CampusEnergyPreprocessor.load(prep_path)
    iso_package = joblib.load(iso_path)
    lstm_bundle = joblib.load(lstm_path)

    # -------------------------------------------------------------
    # 4. Evaluate Random Forest Regressor on Held-Out Test Split
    # -------------------------------------------------------------
    X_test_rf = preprocessor.transform(test_df)
    y_test = test_df["energy_kwh"].values.astype(float)
    rf_preds = rf_model.predict(X_test_rf)
    rf_residuals = y_test - rf_preds
    rf_rel_dev = np.where(rf_preds > 0.1, (np.abs(rf_residuals) / rf_preds) * 100, 0.0)

    rf_mae = float(mean_absolute_error(y_test, rf_preds))
    rf_rmse = float(np.sqrt(mean_squared_error(y_test, rf_preds)))
    rf_r2 = float(r2_score(y_test, rf_preds))

    print(f"RANDOM FOREST (v1) ON TEST SPLIT:")
    print(f"  Test MAE  : {rf_mae:.2f} kWh")
    print(f"  Test RMSE : {rf_rmse:.2f} kWh")
    print(f"  Test R²   : {rf_r2:.4f}")
    print("-" * 75)

    # -------------------------------------------------------------
    # 5. Evaluate Deep Learning LSTM on Chronological Sequences
    # -------------------------------------------------------------
    scaler_x = lstm_bundle["scaler_x"]
    scaler_y = lstm_bundle["scaler_y"]
    test_df_lstm = _engineer_lstm_features(test_df)
    test_scaled = test_df_lstm.copy()
    test_scaled[SEQUENCE_FEATURES] = scaler_x.transform(test_df_lstm[SEQUENCE_FEATURES].values)

    X_test_seq, y_test_seq_scaled = _build_sequences(test_scaled, seq_length=SEQUENCE_LENGTH)
    y_test_seq_scaled = scaler_y.transform(y_test_seq_scaled)

    # Reconstruct LSTM model from weights
    cfg = lstm_bundle["config"]
    lstm_model = CITLSTMRegressor(
        input_dim=cfg["input_dim"],
        hidden_dim=cfg["hidden_dim"],
        sequence_length=cfg["sequence_length"],
        random_state=42
    )
    weights = lstm_bundle["model_weights"]
    lstm_model.W = weights["W"]
    lstm_model.U = weights["U"]
    lstm_model.b = weights["b"]
    lstm_model.Wy = weights["Wy"]
    lstm_model.by = weights["by"]

    lstm_preds_scaled = lstm_model.predict(X_test_seq)
    lstm_preds = scaler_y.inverse_transform(lstm_preds_scaled).flatten()
    lstm_y_true = scaler_y.inverse_transform(y_test_seq_scaled).flatten()

    lstm_mae = float(mean_absolute_error(lstm_y_true, lstm_preds))
    lstm_rmse = float(np.sqrt(mean_squared_error(lstm_y_true, lstm_preds)))
    lstm_r2 = float(r2_score(lstm_y_true, lstm_preds))

    print(f"LSTM SEQUENCE MODEL (v1) ON TEST SEQUENCES ({len(X_test_seq)} sequences):")
    print(f"  Test MAE  : {lstm_mae:.2f} kWh")
    print(f"  Test RMSE : {lstm_rmse:.2f} kWh")
    print(f"  Test R²   : {lstm_r2:.4f}")
    print("-" * 75)

    # -------------------------------------------------------------
    # 6. Evaluate Isolation Forest on Held-Out Test Split
    # -------------------------------------------------------------
    iso_model = iso_package["model"]
    iso_scaler = iso_package["scaler"]
    df_feat_test = preprocessor._engineer_features(test_df)
    X_test_iso_raw = prepare_isolation_features(df_feat_test)
    X_test_iso_scaled = iso_scaler.transform(X_test_iso_raw)

    iso_scores = iso_model.decision_function(X_test_iso_scaled)
    iso_preds = iso_model.predict(X_test_iso_scaled)

    iso_outlier_count = int(np.sum(iso_preds == -1))
    iso_inlier_count = int(np.sum(iso_preds == 1))
    iso_outlier_pct = round((iso_outlier_count / len(test_df)) * 100, 2)

    # Ground-truth labelled anomaly evaluation
    test_labels = test_df["is_anomaly"].values.astype(bool)
    test_pred_anomaly = (iso_preds == -1)

    tp = int(np.sum(test_pred_anomaly & test_labels))
    fp = int(np.sum(test_pred_anomaly & ~test_labels))
    fn = int(np.sum(~test_pred_anomaly & test_labels))
    tn = int(np.sum(~test_pred_anomaly & ~test_labels))

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    print(f"ISOLATION FOREST (v1) ON TEST SPLIT:")
    print(f"  Test Outliers Detected : {iso_outlier_count} / {len(test_df)} ({iso_outlier_pct}%)")
    print(f"  Ground-Truth Anomalies : {int(np.sum(test_labels))}")
    print(f"  Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
    print("-" * 75)

    # -------------------------------------------------------------
    # 7. Generate metrics.json
    # -------------------------------------------------------------
    metrics_payload = {
        "system": "CIT Coimbatore Campus Energy Consumption & Anomaly Detection System",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "dataset": {
            "name": "CIT Coimbatore Synthetic Hourly Campus Energy Dataset",
            "total_records": total_records,
            "seed": 42,
            "split_policy": "strict_chronological_no_leakage",
            "train_split": {
                "count": len(train_df),
                "ratio": 0.80,
                "start": train_start.isoformat(),
                "end": train_end.isoformat(),
            },
            "test_split": {
                "count": len(test_df),
                "ratio": 0.20,
                "start": test_start.isoformat(),
                "end": test_end.isoformat(),
            }
        },
        "random_forest": {
            "model_version": "rf_expected_v1",
            "algorithm": "RandomForestRegressor",
            "hyperparameters": {
                "n_estimators": 120,
                "max_depth": 16,
                "min_samples_split": 4,
                "min_samples_leaf": 2,
                "random_state": 42,
            },
            "test_metrics": {
                "mae_kwh": round(rf_mae, 3),
                "rmse_kwh": round(rf_rmse, 3),
                "r2_score": round(rf_r2, 4),
            },
            "artifact_file": "rf_expected_v1.joblib"
        },
        "lstm": {
            "model_version": "lstm_expected_v1",
            "algorithm": "CITLSTMRegressor (NumPy Sequence Model with BPTT)",
            "sequence_length_hours": SEQUENCE_LENGTH,
            "prediction_horizon": PREDICTION_HORIZON,
            "test_metrics": {
                "mae_kwh": round(lstm_mae, 3),
                "rmse_kwh": round(lstm_rmse, 3),
                "r2_score": round(lstm_r2, 4),
                "test_sequences": len(X_test_seq),
            },
            "artifact_file": "lstm_expected_v1.joblib"
        },
        "isolation_forest": {
            "model_version": "iso_forest_v1",
            "algorithm": "IsolationForest",
            "contamination": 0.04,
            "test_evaluation": {
                "total_test_observations": len(test_df),
                "outliers_flagged": iso_outlier_count,
                "outlier_percentage": iso_outlier_pct,
                "score_min": round(float(iso_scores.min()), 4),
                "score_max": round(float(iso_scores.max()), 4),
                "labelled_test_anomalies": int(np.sum(test_labels)),
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "true_negatives": tn,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
            },
            "artifact_file": "iso_forest_v1.joblib"
        }
    }

    # Save to backend/ml/saved_models/metrics.json and mirror to ml/saved_models/metrics.json
    backend_metrics_path = os.path.join(model_dir, "metrics.json")
    with open(backend_metrics_path, "w") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"Saved metrics summary to: {backend_metrics_path}")

    root_model_dir = os.path.abspath(os.path.join(model_dir, "../../../ml/saved_models"))
    if os.path.exists(root_model_dir):
        root_metrics_path = os.path.join(root_model_dir, "metrics.json")
        with open(root_metrics_path, "w") as f:
            json.dump(metrics_payload, f, indent=2)
        print(f"Mirrored metrics summary to: {root_metrics_path}")

    # -------------------------------------------------------------
    # 8. Generate test_predictions.csv
    # -------------------------------------------------------------
    test_pred_df = pd.DataFrame({
        "timestamp": test_df["timestamp"].values,
        "building_code": test_df["building_code"].values,
        "building_name": test_df["building_name"].values,
        "building_category": test_df["building_category"].values,
        "actual_energy_kwh": np.round(y_test, 2),
        "rf_predicted_kwh": np.round(rf_preds, 2),
        "rf_residual_kwh": np.round(rf_residuals, 2),
        "rf_deviation_pct": np.round(rf_rel_dev, 2),
        "iso_forest_score": np.round(iso_scores, 4),
        "iso_forest_is_outlier": iso_preds == -1,
        "is_synthetic_anomaly_ground_truth": test_labels,
        "anomaly_type": test_df["anomaly_type"].values if "anomaly_type" in test_df.columns else "normal",
        "notes": test_df["notes"].fillna("").values,
    })

    backend_csv_path = os.path.join(model_dir, "test_predictions.csv")
    test_pred_df.to_csv(backend_csv_path, index=False)
    print(f"Saved test predictions ({len(test_pred_df)} rows) to: {backend_csv_path}")

    if os.path.exists(root_model_dir):
        root_csv_path = os.path.join(root_model_dir, "test_predictions.csv")
        test_pred_df.to_csv(root_csv_path, index=False)
        print(f"Mirrored test predictions to: {root_csv_path}")

    print("=" * 75)
    return metrics_payload


if __name__ == "__main__":
    evaluate_models_and_export_predictions()

