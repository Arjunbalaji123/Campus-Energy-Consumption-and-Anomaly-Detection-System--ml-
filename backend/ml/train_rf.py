"""Offline Training Pipeline for Random Forest Campus Energy Predictor.

Trains RandomForestRegressor on chronological historical observations,
evaluates MAE, RMSE, and R2 on unseen test period, registers the model
artifact in the database, and serializes artifacts via Joblib.
"""
import os
import sys
import json
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import ModelVersion, ModelEvaluationRun, EnergyReading, Prediction, Building
from ml.preprocessing import CampusEnergyPreprocessor, chronological_train_test_split, FEATURE_COLUMNS, TARGET_COLUMN
from ml.eda import load_dataset


def train_random_forest_model(
    test_ratio: float = 0.20,
    n_estimators: int = 120,
    max_depth: int = 16,
    save_artifacts: bool = True,
    generate_baseline_predictions: bool = True
) -> dict:
    """Train and evaluate Random Forest Regressor on campus energy data."""
    print("=" * 70)
    print("CIT COIMBATORE - RANDOM FOREST EXPECTED ENERGY MODEL TRAINING")
    print("=" * 70)

    # 1. Load Data
    df = load_dataset()
    print(f"Loaded {len(df)} total observations.")

    # 2. Chronological Train/Test Split
    train_df, test_df = chronological_train_test_split(df, test_ratio=test_ratio)
    train_start, train_end = train_df["timestamp"].min(), train_df["timestamp"].max()
    test_start, test_end = test_df["timestamp"].min(), test_df["timestamp"].max()

    print(f"Train split : {len(train_df)} rows ({train_start.strftime('%Y-%m-%d')} to {train_end.strftime('%Y-%m-%d')})")
    print(f"Test split  : {len(test_df)} rows ({test_start.strftime('%Y-%m-%d')} to {test_end.strftime('%Y-%m-%d')})")

    # 3. Fit Preprocessor strictly on Training Set
    preprocessor = CampusEnergyPreprocessor()
    preprocessor.fit(train_df)

    X_train = preprocessor.transform(train_df)
    y_train = train_df[TARGET_COLUMN].values

    X_test = preprocessor.transform(test_df)
    y_test = test_df[TARGET_COLUMN].values

    # 4. Train RandomForestRegressor
    hyperparameters = {
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "min_samples_split": 4,
        "min_samples_leaf": 2,
        "random_state": 42,
        "n_jobs": -1,
    }
    rf = RandomForestRegressor(**hyperparameters)
    print("Fitting RandomForestRegressor...")
    rf.fit(X_train, y_train)

    # 5. Evaluate Metrics
    train_preds = rf.predict(X_train)
    test_preds = rf.predict(X_test)

    train_mae = float(mean_absolute_error(y_train, train_preds))
    train_rmse = float(np.sqrt(mean_squared_error(y_train, train_preds)))
    train_r2 = float(r2_score(y_train, train_preds))

    test_mae = float(mean_absolute_error(y_test, test_preds))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, test_preds)))
    test_r2 = float(r2_score(y_test, test_preds))

    print("-" * 70)
    print("MODEL EVALUATION PERFORMANCE:")
    print(f"  Train Set -> MAE: {train_mae:.2f} kWh | RMSE: {train_rmse:.2f} kWh | R²: {train_r2:.4f}")
    print(f"  Test Set  -> MAE: {test_mae:.2f} kWh | RMSE: {test_rmse:.2f} kWh | R²: {test_r2:.4f}")
    print("-" * 70)

    # 6. Top Feature Importances
    importances = rf.feature_importances_
    indices = np.argsort(importances)[::-1]
    print("TOP 5 PREDICTIVE FEATURES:")
    top_features = {}
    for i in range(min(5, len(indices))):
        feat = FEATURE_COLUMNS[indices[i]]
        imp = float(importances[indices[i]])
        top_features[feat] = round(imp, 4)
        print(f"  {i+1}. {feat:<22}: {imp * 100:.2f}% relative importance")
    print("-" * 70)

    # 7. Serialize Artifacts
    model_dir = os.path.abspath(settings.MODEL_DIR)
    os.makedirs(model_dir, exist_ok=True)

    version_tag = "rf_expected_v1"
    model_path = os.path.join(model_dir, f"{version_tag}.joblib")
    preprocessor_path = os.path.join(model_dir, "preprocessor.joblib")

    if save_artifacts:
        joblib.dump(rf, model_path)
        preprocessor.save(preprocessor_path)
        print(f"Saved model artifact        : {model_path}")
        print(f"Saved preprocessor artifact : {preprocessor_path}")

    # 8. Register in Database
    metrics_summary = {
        "train": {"mae": round(train_mae, 3), "rmse": round(train_rmse, 3), "r2": round(train_r2, 4)},
        "test": {"mae": round(test_mae, 3), "rmse": round(test_rmse, 3), "r2": round(test_r2, 4)},
        "top_features": top_features,
    }

    db = SessionLocal()
    try:
        # Check if version tag exists
        existing_version = db.query(ModelVersion).filter(ModelVersion.version_tag == version_tag).first()
        if existing_version:
            mv = existing_version
            mv.file_path = model_path
            mv.hyperparameters = hyperparameters
            mv.metrics = metrics_summary
            mv.trained_at = datetime.utcnow()
            mv.is_active = True
        else:
            mv = ModelVersion(
                model_name="CIT Campus Energy Random Forest Predictor",
                algorithm="RandomForestRegressor",
                version_tag=version_tag,
                file_path=model_path,
                hyperparameters=hyperparameters,
                metrics=metrics_summary,
                is_active=True,
                notes="Trained on chronological 80% split with cyclical time features and building profiles.",
            )
            db.add(mv)
        db.flush()

        # Add Evaluation Run record
        eval_run = ModelEvaluationRun(
            model_version_id=mv.id,
            dataset_name="CIT Synthetic Hourly Dataset",
            test_period_start=test_start,
            test_period_end=test_end,
            sample_count=len(test_df),
            mae=round(test_mae, 3),
            rmse=round(test_rmse, 3),
            r2_score=round(test_r2, 4),
            notes="Evaluated strictly on unseen future test window.",
        )
        db.add(eval_run)
        db.commit()
        print(f"Registered ModelVersion ID={mv.id} and EvaluationRun ID={eval_run.id} in database.")

        # 9. Optionally populate predictions table for recent readings
        if generate_baseline_predictions:
            print("Generating baseline predictions for test observations...")
            db.query(Prediction).filter(Prediction.model_version_id == mv.id).delete()
            db.commit()

            # Predict on full dataset
            X_all = preprocessor.transform(df)
            y_pred_all = rf.predict(X_all)

            prediction_records = []
            for idx, row in df.iterrows():
                actual_kwh = float(row["energy_kwh"])
                pred_kwh = max(1.0, float(y_pred_all[idx])) # physical floor
                residual = actual_kwh - pred_kwh
                dev_pct = (residual / pred_kwh) * 100.0 if pred_kwh > 0.1 else None

                prediction_records.append(Prediction(
                    reading_id=int(row["id"]),
                    building_id=int(row["building_id"] if "building_id" in row else db.query(Building.id).filter(Building.code == row["building_code"]).scalar()),
                    model_version_id=mv.id,
                    predicted_energy_kwh=round(pred_kwh, 2),
                    residual_kwh=round(residual, 2),
                    deviation_pct=round(dev_pct, 2) if dev_pct is not None else None,
                ))

                if len(prediction_records) >= 500:
                    db.bulk_save_objects(prediction_records)
                    db.commit()
                    prediction_records = []

            if prediction_records:
                db.bulk_save_objects(prediction_records)
                db.commit()

            print(f"Populated {len(df)} predictions in database.")

    finally:
        db.close()

    print("=" * 70)
    return {
        "version_tag": version_tag,
        "metrics": metrics_summary,
        "test_mae": test_mae,
        "test_rmse": test_rmse,
        "test_r2": test_r2,
    }


if __name__ == "__main__":
    train_random_forest_model()

