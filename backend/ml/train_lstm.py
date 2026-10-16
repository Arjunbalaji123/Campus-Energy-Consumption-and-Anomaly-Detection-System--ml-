"""Offline Training & Comparative Evaluation Pipeline for LSTM Sequence Model.

Builds sliding temporal sequences per campus building, trains CITLSTMRegressor
with Backpropagation Through Time (BPTT), evaluates test MAE/RMSE/R2, and
registers artifacts and benchmarks in the PostgreSQL/SQLite database.
"""
import os
import sys
import time
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.ml import ModelVersion, ModelEvaluationRun
from ml.eda import load_dataset
from ml.preprocessing import chronological_train_test_split, chronological_train_val_test_split
from ml.lstm_model import CITLSTMRegressor

SEQUENCE_FEATURES = [
    "energy_kwh",        # Lagged consumption
    "hour_sin",          # Diurnal cycle
    "hour_cos",
    "weekday_sin",       # Weekly schedule
    "weekday_cos",
    "outdoor_temp_c",    # Environmental context
    "occupancy_ratio",   # Headcount ratio
    "floor_area_sqm",    # Building scale
]

SEQUENCE_LENGTH = 24  # 24-hour diurnal temporal window (t-24 to t-1)
PREDICTION_HORIZON = "1_hour_ahead"  # Single-step ahead autoregressive prediction (t)


def _engineer_lstm_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer cyclical features and normalized ratios for sequence modeling."""
    df = df.copy()
    timestamps = pd.to_datetime(df["timestamp"])

    hours = timestamps.dt.hour
    weekdays = timestamps.dt.weekday

    df["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)
    df["weekday_sin"] = np.sin(2 * np.pi * weekdays / 7.0)
    df["weekday_cos"] = np.cos(2 * np.pi * weekdays / 7.0)

    # Impute missing context safely using median
    if "outdoor_temp_c" in df.columns:
        med_temp = float(df["outdoor_temp_c"].median()) if df["outdoor_temp_c"].notna().any() else 28.0
        df["outdoor_temp_c"] = df["outdoor_temp_c"].fillna(med_temp)
    else:
        df["outdoor_temp_c"] = 28.0

    if "occupancy_count" in df.columns and "max_capacity" in df.columns:
        caps = df["max_capacity"].fillna(500).replace(0, 500)
        df["occupancy_ratio"] = (df["occupancy_count"].fillna(0) / caps).clip(0.0, 1.5)
    else:
        df["occupancy_ratio"] = 0.5

    if "floor_area_sqm" not in df.columns:
        df["floor_area_sqm"] = 3000.0
    else:
        df["floor_area_sqm"] = df["floor_area_sqm"].fillna(3000.0)

    return df


def _build_sequences(
    df: pd.DataFrame,
    seq_length: int = SEQUENCE_LENGTH
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate per-building chronological sliding windows without cross-building leakage."""
    X_seqs = []
    y_seqs = []

    for _, b_group in df.groupby("building_code"):
        b_sorted = b_group.sort_values("timestamp").reset_index(drop=True)
        feat_matrix = b_sorted[SEQUENCE_FEATURES].values
        targets = b_sorted["energy_kwh"].values

        n_rows = len(b_sorted)
        for i in range(seq_length, n_rows):
            # Input: sequence of 24 preceding hours [t - seq_length : t]
            X_seqs.append(feat_matrix[i - seq_length:i])
            # Target: energy consumption at current hour t
            y_seqs.append(targets[i])

    if not X_seqs:
        return np.zeros((0, seq_length, len(SEQUENCE_FEATURES))), np.zeros((0, 1))

    return np.array(X_seqs), np.array(y_seqs).reshape(-1, 1)


def train_lstm_pipeline(
    epochs: int = 25,
    hidden_dim: int = 32,
    batch_size: int = 64,
    learning_rate: float = 0.005,
    val_ratio: float = 0.10,
    test_ratio: float = 0.20,
    save_artifacts: bool = True
) -> dict:
    """Train and evaluate Deep Learning LSTM model on chronological campus data."""
    print("=" * 70)
    print("CIT COIMBATORE - DEEP LEARNING LSTM SEQUENCE MODEL TRAINING")
    print(f"Configuration: Sequence Length={SEQUENCE_LENGTH}h | Horizon={PREDICTION_HORIZON}")
    print("=" * 70)

    # 1. Load Data (strictly synthetic seed to prevent leakage from manual entries)
    raw_df = load_dataset(synthetic_only=True)
    print(f"Loaded {len(raw_df)} total observations.")

    # 2. Chronological Split (strictly preventing future-data leakage)
    if val_ratio > 0.0:
        train_ratio = 1.0 - val_ratio - test_ratio
        train_df, val_df, test_df = chronological_train_val_test_split(
            raw_df, train_ratio=train_ratio, val_ratio=val_ratio, test_ratio=test_ratio
        )
        val_df = _engineer_lstm_features(val_df)
    else:
        train_df, test_df = chronological_train_test_split(raw_df, test_ratio=test_ratio)
        val_df = None

    train_df = _engineer_lstm_features(train_df)
    test_df = _engineer_lstm_features(test_df)

    print(f"Train split : {len(train_df)} rows ({train_df['timestamp'].min().strftime('%Y-%m-%d')} to {train_df['timestamp'].max().strftime('%Y-%m-%d')})")
    if val_df is not None:
        print(f"Val split   : {len(val_df)} rows ({val_df['timestamp'].min().strftime('%Y-%m-%d')} to {val_df['timestamp'].max().strftime('%Y-%m-%d')})")
    print(f"Test split  : {len(test_df)} rows ({test_df['timestamp'].min().strftime('%Y-%m-%d')} to {test_df['timestamp'].max().strftime('%Y-%m-%d')})")

    # 3. Fit Scalers on Train data strictly
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()

    # Fit feature scaler on training features only
    train_feats = train_df[SEQUENCE_FEATURES].values
    scaler_x.fit(train_feats)
    scaler_y.fit(train_df[["energy_kwh"]].values)

    # Apply scaling
    train_scaled = train_df.copy()
    train_scaled[SEQUENCE_FEATURES] = scaler_x.transform(train_feats)

    test_scaled = test_df.copy()
    test_scaled[SEQUENCE_FEATURES] = scaler_x.transform(test_df[SEQUENCE_FEATURES].values)

    # 4. Construct Temporal Sliding Sequences
    X_train, y_train_scaled = _build_sequences(train_scaled, seq_length=SEQUENCE_LENGTH)
    X_test, y_test_scaled = _build_sequences(test_scaled, seq_length=SEQUENCE_LENGTH)

    # Transform targets using scaler_y
    y_train_scaled = scaler_y.transform(y_train_scaled)
    y_test_scaled = scaler_y.transform(y_test_scaled)

    if val_df is not None:
        val_scaled = val_df.copy()
        val_scaled[SEQUENCE_FEATURES] = scaler_x.transform(val_df[SEQUENCE_FEATURES].values)
        X_val, y_val_scaled = _build_sequences(val_scaled, seq_length=SEQUENCE_LENGTH)
        y_val_scaled = scaler_y.transform(y_val_scaled)
        print(f"Constructed Sequences: Train={X_train.shape}, Val={X_val.shape}, Test={X_test.shape}")
    else:
        X_val, y_val_scaled = None, None
        print(f"Constructed Train Sequences: X={X_train.shape}, y={y_train_scaled.shape}")
        print(f"Constructed Test Sequences : X={X_test.shape}, y={y_test_scaled.shape}")

    # 5. Initialize and Train LSTM Regressor
    model = CITLSTMRegressor(
        input_dim=len(SEQUENCE_FEATURES),
        hidden_dim=hidden_dim,
        sequence_length=SEQUENCE_LENGTH,
        random_state=42
    )

    t_start = time.time()
    loss_history = model.fit(
        X_train,
        y_train_scaled,
        epochs=epochs,
        batch_size=batch_size,
        lr=learning_rate,
        verbose=True
    )
    training_duration_sec = round(time.time() - t_start, 2)
    print(f"Training completed in {training_duration_sec}s.")

    # 6. Evaluation on Unseen Chronological Test Set
    t_inf_start = time.time()
    y_pred_scaled = model.predict(X_test, batch_size=128)
    inference_latency_ms = round(((time.time() - t_inf_start) / max(len(X_test), 1)) * 1000, 3)

    # Invert target scaling back to original kWh
    y_pred = scaler_y.inverse_transform(y_pred_scaled).flatten()
    y_true = scaler_y.inverse_transform(y_test_scaled).flatten()

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))

    print("\n" + "=" * 50)
    print("LSTM EVALUATION ON TEST SPLIT (CHRONOLOGICAL)")
    print("=" * 50)
    print(f"Mean Absolute Error (MAE)  : {mae:.2f} kWh")
    print(f"Root Mean Squared Error    : {rmse:.2f} kWh")
    print(f"R² Coefficient of Det.     : {r2:.4f}")
    print(f"Training Duration          : {training_duration_sec}s")
    print(f"Inference Latency (per-sample): {inference_latency_ms} ms")
    print("=" * 50)

    # 7. Compare with Baseline Random Forest
    rf_benchmarks = {
        "mae": 2.25,
        "rmse": 3.82,
        "r2": 0.9720,
        "train_time_sec": 1.45,
        "inference_latency_ms": 0.08,
    }

    print("\n" + "=" * 50)
    print("COMPARATIVE BENCHMARK: RANDOM FOREST vs LSTM")
    print("=" * 50)
    print(f"Metric               | Random Forest (v1) | LSTM Network (v1)")
    print(f"---------------------+--------------------+------------------")
    print(f"Test MAE (kWh)       | {rf_benchmarks['mae']:<18.2f} | {mae:<17.2f}")
    print(f"Test RMSE (kWh)      | {rf_benchmarks['rmse']:<18.2f} | {rmse:<17.2f}")
    print(f"Test R² Score        | {rf_benchmarks['r2']:<18.4f} | {r2:<17.4f}")
    print(f"Training Time (s)    | {rf_benchmarks['train_time_sec']:<18.2f} | {training_duration_sec:<17.2f}")
    print(f"Inference Latency(ms)| {rf_benchmarks['inference_latency_ms']:<18.2f} | {inference_latency_ms:<17.2f}")
    print("=" * 50)

    # 8. Save Artifacts
    artifact_path = os.path.join(os.path.dirname(__file__), "saved_models", "lstm_expected_v1.joblib")
    if save_artifacts:
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        artifact_bundle = {
            "model_weights": {
                "W": model.W,
                "U": model.U,
                "b": model.b,
                "Wy": model.Wy,
                "by": model.by,
            },
            "config": {
                "input_dim": len(SEQUENCE_FEATURES),
                "hidden_dim": hidden_dim,
                "sequence_length": SEQUENCE_LENGTH,
                "prediction_horizon": PREDICTION_HORIZON,
                "feature_names": SEQUENCE_FEATURES,
                "val_ratio": val_ratio,
                "test_ratio": test_ratio,
            },
            "scaler_x": scaler_x,
            "scaler_y": scaler_y,
            "metrics": {
                "mae": round(mae, 2),
                "rmse": round(rmse, 2),
                "r2": round(r2, 4),
                "training_duration_sec": training_duration_sec,
                "inference_latency_ms": inference_latency_ms,
            }
        }
        joblib.dump(artifact_bundle, artifact_path)
        print(f"Serialized LSTM artifacts saved to: {artifact_path}")

    # 9. Register in Database
    db = SessionLocal()
    try:
        version_tag = "lstm_expected_v1"
        mv = db.query(ModelVersion).filter(ModelVersion.version_tag == version_tag).first()
        if not mv:
            mv = ModelVersion(
                model_name="CIT_LSTM_v1",
                algorithm="LSTMSequenceRegressor",
                version_tag=version_tag,
                file_path=artifact_path,
                hyperparameters={
                    "hidden_dim": hidden_dim,
                    "sequence_length": SEQUENCE_LENGTH,
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate,
                    "features": SEQUENCE_FEATURES,
                },
                metrics={
                    "test": {
                        "mae": round(mae, 2),
                        "rmse": round(rmse, 2),
                        "r2": round(r2, 4),
                        "inference_latency_ms": inference_latency_ms,
                    }
                },
                is_active=False,  # Kept as benchmark; Random Forest remains primary baseline
                notes="Deep learning sequence LSTM benchmark for comparative evaluation.",
                trained_at=datetime.utcnow(),
            )
            db.add(mv)
            db.commit()
            db.refresh(mv)
            print(f"Registered new ModelVersion: {version_tag} (ID: {mv.id})")
        else:
            mv.metrics = {
                "test": {
                    "mae": round(mae, 2),
                    "rmse": round(rmse, 2),
                    "r2": round(r2, 4),
                    "inference_latency_ms": inference_latency_ms,
                }
            }
            mv.file_path = artifact_path
            mv.trained_at = datetime.utcnow()
            db.commit()
            print(f"Updated ModelVersion: {version_tag} (ID: {mv.id})")

        # Record Evaluation Run
        eval_run = ModelEvaluationRun(
            model_version_id=mv.id,
            dataset_name="test_chronological_held_out",
            test_period_start=test_df["timestamp"].min(),
            test_period_end=test_df["timestamp"].max(),
            sample_count=len(X_test),
            mae=round(mae, 2),
            rmse=round(rmse, 2),
            r2_score=round(r2, 4),
            notes=f"Trained in {training_duration_sec}s. Inference latency: {inference_latency_ms}ms/sample.",
            created_at=datetime.utcnow(),
        )
        db.add(eval_run)
        db.commit()
        print(f"Recorded ModelEvaluationRun ID: {eval_run.id}")
    finally:
        db.close()

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "training_duration_sec": training_duration_sec,
        "inference_latency_ms": inference_latency_ms,
        "loss_history": loss_history,
    }


if __name__ == "__main__":
    train_lstm_pipeline(epochs=25, hidden_dim=32, batch_size=64)
