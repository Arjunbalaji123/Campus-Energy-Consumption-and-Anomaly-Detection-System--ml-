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
from ml.preprocessing import CampusEnergyPreprocessor
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
    save_artifacts: bool = True
) -> dict:
    """Train unsupervised Isolation Forest on campus observations."""
    print("=" * 70)
    print("CIT COIMBATORE - ISOLATION FOREST OUTLIER DETECTOR TRAINING")
    print("=" * 70)

    # 1. Load Data
    df = load_dataset()
    print(f"Loaded {len(df)} total observations for unsupervised anomaly training.")

    # 2. Extract Preprocessed Features
    preprocessor = CampusEnergyPreprocessor()
    df_feat = preprocessor._engineer_features(df)

    X_raw = prepare_isolation_features(df_feat)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    iso = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    print(f"Fitting IsolationForest (contamination={contamination}, n_estimators={n_estimators})...")
    iso.fit(X_scaled)

    scores = iso.decision_function(X_scaled)
    preds = iso.predict(X_scaled)

    outlier_count = int(np.sum(preds == -1))
    inlier_count = int(np.sum(preds == 1))
    outlier_pct = round((outlier_count / len(df)) * 100, 2)

    print("-" * 70)
    print("ISOLATION FOREST DIAGNOSTICS:")
    print(f"  Total Observations : {len(df)}")
    print(f"  Inliers Detected   : {inlier_count} ({100 - outlier_pct:.2f}%)")
    print(f"  Outliers Flagged   : {outlier_count} ({outlier_pct:.2f}%)")
    print(f"  Decision Score Min : {scores.min():.4f} (most isolated)")
    print(f"  Decision Score Max : {scores.max():.4f} (most typical)")
    print("-" * 70)

    # 3. Check Injected Anomaly Detection
    injected_mask = df["notes"].str.contains("INJECTED_ANOMALY", na=False)
    injected_indices = df[injected_mask].index
    injected_detected = int(np.sum(preds[injected_indices] == -1))
    total_injected = len(injected_indices)
    print(f"INJECTED ANOMALY CAPTURE RATE: {injected_detected}/{total_injected} ({injected_detected/total_injected*100:.1f}%)")
    for idx in injected_indices:
        r = df.loc[idx]
        print(f"  • [{r['building_code']}] {r['energy_kwh']} kWh | Score: {scores[idx]:.4f} | Outlier: {preds[idx] == -1}")
    print("-" * 70)

    # 4. Save Artifacts using clean dict of standard sklearn objects
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

    # 5. Register in Database
    hyperparameters = {
        "n_estimators": n_estimators,
        "contamination": contamination,
        "features": ISOLATION_FEATURES,
    }
    metrics = {
        "outlier_count": outlier_count,
        "inlier_count": inlier_count,
        "outlier_pct": outlier_pct,
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
        "outlier_count": outlier_count,
        "outlier_pct": outlier_pct,
        "injected_detected": f"{injected_detected}/{total_injected}",
    }


if __name__ == "__main__":
    train_isolation_forest_model()

