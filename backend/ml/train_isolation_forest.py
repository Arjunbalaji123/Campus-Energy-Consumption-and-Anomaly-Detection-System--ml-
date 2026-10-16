"""Isolation Forest Training and Artifact Serialization for CIT Campus Energy System.

Trains an unsupervised IsolationForest model on standardized multidimensional energy,
energy-intensity (kWh/m²), and context features to detect geometric outliers in feature space.
Uses native scikit-learn serialization dictionary for complete unpickling portability.
"""
import os
import sys
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import ModelVersion
from ml.preprocessing import CampusEnergyPreprocessor, chronological_train_test_split
from ml.eda import load_dataset

ISOLATION_FEATURES = [
    "energy_kwh",
    "kwh_per_sqm",
    "occupancy_ratio",
    "outdoor_temp_c",
    "relative_humidity",
    "hour_sin", "hour_cos",
    "is_weekend",
    "cat_IT Block",
    "cat_Laboratory Block",
    "cat_Academic Block",
    "cat_Workshop / Equipment Block",
    "cat_Library",
    "cat_Main Block",
]


def prepare_isolation_features(df_feat: pd.DataFrame) -> np.ndarray:
    """Derive energy intensity (kWh/m2) and extract feature matrix."""
    df_feat = df_feat.copy()
    df_feat["kwh_per_sqm"] = df_feat["energy_kwh"] / df_feat["floor_area_sqm"].clip(lower=100.0)
    return df_feat[ISOLATION_FEATURES].values


def train_isolation_forest_model(
    contamination: float = 0.04,
    n_estimators: int = 150,
    test_ratio: float = 0.20,
    save_artifacts: bool = True
) -> dict:
    """Train unsupervised Isolation Forest on training split and evaluate on held-out test split."""
    print("=" * 70)
    print("CIT COIMBATORE - ISOLATION FOREST OUTLIER DETECTOR TRAINING")
    print("=" * 70)

    # 1. Load Synthetic Benchmark Data
    df = load_dataset(synthetic_only=True)
    print(f"Loaded {len(df)} total observations.")

    # 2. Chronological Train / Test Split (Strictly Preventing Future Data Leakage)
    train_df, test_df = chronological_train_test_split(df, test_ratio=test_ratio)
    train_start, train_end = train_df["timestamp"].min(), train_df["timestamp"].max()
    test_start, test_end = test_df["timestamp"].min(), test_df["timestamp"].max()

    print(f"Train split : {len(train_df)} rows ({train_start.strftime('%Y-%m-%d')} to {train_end.strftime('%Y-%m-%d')})")
    print(f"Test split  : {len(test_df)} rows ({test_start.strftime('%Y-%m-%d')} to {test_end.strftime('%Y-%m-%d')})")

    # 3. Fit Preprocessor and Scaler strictly on Training Data
    preprocessor = CampusEnergyPreprocessor()
    df_feat_train = preprocessor._engineer_features(train_df)
    X_train_raw = prepare_isolation_features(df_feat_train)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw)

    # 4. Fit Isolation Forest Strictly on Training Set
    iso = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    print(f"Fitting IsolationForest on train split (contamination={contamination}, n_estimators={n_estimators})...")
    iso.fit(X_train_scaled)

    train_scores = iso.decision_function(X_train_scaled)
    train_preds = iso.predict(X_train_scaled)
    train_outliers = int(np.sum(train_preds == -1))
    train_outlier_pct = round((train_outliers / len(train_df)) * 100, 2)

    # 5. Evaluate on Held-Out Test Set (Unseen Observations)
    df_feat_test = preprocessor._engineer_features(test_df)
    X_test_raw = prepare_isolation_features(df_feat_test)
    X_test_scaled = scaler.transform(X_test_raw)  # Transform test using train-fitted scaler

    test_scores = iso.decision_function(X_test_scaled)
    test_preds = iso.predict(X_test_scaled)

    test_outlier_count = int(np.sum(test_preds == -1))
    test_inlier_count = int(np.sum(test_preds == 1))
    test_outlier_pct = round((test_outlier_count / len(test_df)) * 100, 2)

    print("-" * 70)
    print("HELD-OUT TEST SPLIT EVALUATION (UNSEEN FUTURE OBSERVATIONS):")
    print(f"  Test Observations  : {len(test_df)}")
    print(f"  Inliers Detected   : {test_inlier_count} ({100 - test_outlier_pct:.2f}%)")
    print(f"  Outliers Flagged   : {test_outlier_count} ({test_outlier_pct:.2f}%)")
    print(f"  Decision Score Min : {test_scores.min():.4f} (most isolated)")
    print(f"  Decision Score Max : {test_scores.max():.4f} (most typical)")
    print("-" * 70)

    # 6. Evaluation against Labelled Synthetic Anomalies
    test_labels = test_df["is_anomaly"].values
    test_pred_anomaly = (test_preds == -1)

    tp = int(np.sum(test_pred_anomaly & test_labels))
    fp = int(np.sum(test_pred_anomaly & ~test_labels))
    fn = int(np.sum(~test_pred_anomaly & test_labels))
    tn = int(np.sum(~test_pred_anomaly & ~test_labels))

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    print("LABELLED SYNTHETIC ANOMALY EVALUATION ON HELD-OUT TEST DATA:")
    print(f"  Ground-Truth Anomalies in Test Set : {int(np.sum(test_labels))}")
    print(f"  True Positives (TP)                : {tp}")
    print(f"  False Positives (FP)               : {fp}")
    print(f"  False Negatives (FN)               : {fn}")
    print(f"  Precision                          : {precision:.4f}")
    print(f"  Recall                             : {recall:.4f}")
    print(f"  F1-Score                           : {f1:.4f}")
    print("-" * 70)

    # 7. Check Injected Anomalies across Full Dataset for Diagnostic Reporting
    df_feat_all = preprocessor._engineer_features(df)
    X_all_scaled = scaler.transform(prepare_isolation_features(df_feat_all))
    all_scores = iso.decision_function(X_all_scaled)
    all_preds = iso.predict(X_all_scaled)

    injected_mask = df["is_anomaly"].values
    injected_indices = np.where(injected_mask)[0]
    injected_detected = int(np.sum(all_preds[injected_indices] == -1))
    total_injected = len(injected_indices)
    print(f"OVERALL INJECTED ANOMALY DIAGNOSTIC CAPTURE: {injected_detected}/{total_injected} ({injected_detected/total_injected*100:.1f}%)")
    for idx in injected_indices:
        r = df.iloc[idx]
        split_type = "TRAIN" if idx < len(train_df) else "TEST"
        print(f"  • [{split_type}] [{r['building_code']}] {r['energy_kwh']} kWh | Score: {all_scores[idx]:.4f} | Outlier: {all_preds[idx] == -1} | Notes: {r['notes'][:45]}...")
    print("-" * 70)

    # 8. Save Artifacts using clean dict of standard sklearn objects
    model_dir = os.path.abspath(settings.MODEL_DIR)
    os.makedirs(model_dir, exist_ok=True)

    version_tag = "iso_forest_v1"
    model_path = os.path.join(model_dir, f"{version_tag}.joblib")

    if save_artifacts:
        artifact_package = {
            "model": iso,
            "scaler": scaler,
            "features": ISOLATION_FEATURES,
        }
        joblib.dump(artifact_package, model_path)
        print(f"Saved portable Isolation Forest artifact: {model_path}")

    # 9. Register in Database
    hyperparameters = {
        "n_estimators": n_estimators,
        "contamination": contamination,
        "features": ISOLATION_FEATURES,
        "train_observations": len(train_df),
        "test_observations": len(test_df),
        "test_ratio": test_ratio,
    }
    metrics = {
        "train_outlier_count": train_outliers,
        "train_outlier_pct": train_outlier_pct,
        "test_outlier_count": test_outlier_count,
        "test_outlier_pct": test_outlier_pct,
        "test_precision": precision,
        "test_recall": recall,
        "test_f1": f1,
        "injected_detected": f"{injected_detected}/{total_injected}",
    }

    db = SessionLocal()
    try:
        existing = db.query(ModelVersion).filter(ModelVersion.version_tag == version_tag).first()
        if existing:
            mv = existing
            mv.file_path = model_path
            mv.hyperparameters = hyperparameters
            mv.metrics = metrics
            mv.trained_at = datetime.utcnow()
            mv.is_active = True
        else:
            mv = ModelVersion(
                model_name="CIT Campus Energy Isolation Forest Outlier Detector",
                algorithm="IsolationForest",
                version_tag=version_tag,
                file_path=model_path,
                hyperparameters=hyperparameters,
                metrics=metrics,
                is_active=True,
                notes="Standardized multivariate outlier detector using energy intensity (kWh/m2), weather, and occupancy.",
            )
            db.add(mv)
        db.commit()
        print(f"Registered ModelVersion ID={mv.id} in database.")
    finally:
        db.close()

    print("=" * 70)
    return {
        "version_tag": version_tag,
        "test_outlier_count": test_outlier_count,
        "test_outlier_pct": test_outlier_pct,
        "test_precision": precision,
        "test_recall": recall,
        "test_f1": f1,
        "injected_detected": f"{injected_detected}/{total_injected}",
    }


if __name__ == "__main__":
    train_isolation_forest_model()

