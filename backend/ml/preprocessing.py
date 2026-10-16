"""Feature Engineering and Preprocessing Pipeline for CIT Campus Energy System.

Provides cyclical temporal encoding, missing context imputation, building metadata
enrichment, and strict chronological train/test splitting to prevent target leakage.
"""
import os
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler
import joblib

# Features used for expected energy prediction
FEATURE_COLUMNS = [
    # Cyclical Time Features
    "hour_sin", "hour_cos",
    "weekday_sin", "weekday_cos",
    "month_sin", "month_cos",
    "is_weekend", "is_holiday",
    
    # Building Static Physical Features
    "floor_area_sqm",
    "max_capacity",
    "has_hvac",
    
    # One-Hot Building Categories
    "cat_Main Block", "cat_IT Block", "cat_Academic Block",
    "cat_Laboratory Block", "cat_Library", "cat_Workshop / Equipment Block",
    "cat_Other Campus Buildings",
    
    # Operational State Features
    "status_normal", "status_reduced", "status_closed",
    
    # Dynamic Environmental & Occupancy Context (robust to missingness)
    "outdoor_temp_c",
    "relative_humidity",
    "occupancy_ratio",
    "is_temp_missing",
    "is_occupancy_missing",
]

TARGET_COLUMN = "energy_kwh"


class CampusEnergyPreprocessor(BaseEstimator, TransformerMixin):
    """Production-grade preprocessor for CIT campus energy observations.
    
    Handles cyclical time transformations, categorical one-hot encoding,
    missing value imputation with indicator flags, and feature scaling.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_names: List[str] = FEATURE_COLUMNS
        self.median_outdoor_temp: float = 28.0
        self.median_humidity: float = 65.0
        self.is_fitted: bool = False

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive cyclical temporal features, operational flags, and context ratios."""
        df = df.copy()

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # 1. Cyclical Temporal Features
        hours = df["timestamp"].dt.hour
        df["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
        df["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)

        weekdays = df["timestamp"].dt.weekday
        df["weekday_sin"] = np.sin(2 * np.pi * weekdays / 7.0)
        df["weekday_cos"] = np.cos(2 * np.pi * weekdays / 7.0)

        months = df["timestamp"].dt.month
        df["month_sin"] = np.sin(2 * np.pi * months / 12.0)
        df["month_cos"] = np.cos(2 * np.pi * months / 12.0)

        df["is_weekend"] = weekdays.isin([5, 6]).astype(float)
        df["is_holiday"] = (df.get("day_type", "working_day") == "holiday").astype(float)

        # 2. Building Physical Metadata
        df["floor_area_sqm"] = df.get("floor_area_sqm", 5000.0).fillna(5000.0).astype(float)
        df["max_capacity"] = df.get("max_capacity", 500.0).fillna(500.0).astype(float)
        df["has_hvac"] = df.get("has_hvac", False).astype(float)

        # 3. Categorical Building Categories One-Hot
        category_col = df.get("building_category", "Other Campus Buildings")
        for cat in [
            "Main Block", "IT Block", "Academic Block", "Laboratory Block",
            "Library", "Workshop / Equipment Block", "Other Campus Buildings"
        ]:
            df[f"cat_{cat}"] = (category_col == cat).astype(float)

        # 4. Operational Status One-Hot
        op_col = df.get("operating_status", "normal")
        for status in ["normal", "reduced", "closed"]:
            df[f"status_{status}"] = (op_col == status).astype(float)

        # 5. Dynamic Context with Missingness Indicators
        df["is_temp_missing"] = df["outdoor_temp_c"].isna().astype(float)
        df["outdoor_temp_c"] = df["outdoor_temp_c"].fillna(self.median_outdoor_temp)

        humidity = df.get("relative_humidity", pd.Series(index=df.index, dtype=float))
        df["relative_humidity"] = humidity.fillna(self.median_humidity)

        # Occupancy Ratio = count / max_capacity
        has_occ = "occupancy_count" in df.columns and df["occupancy_count"].notna().any()
        if has_occ:
            df["is_occupancy_missing"] = df["occupancy_count"].isna().astype(float)
            occ_count = df["occupancy_count"].fillna(0.0)
            df["occupancy_ratio"] = (occ_count / df["max_capacity"]).clip(0.0, 1.5)
        else:
            df["is_occupancy_missing"] = 1.0
            df["occupancy_ratio"] = 0.0

        return df

    def fit(self, X: pd.DataFrame, y=None):
        """Fit preprocessor and feature scaler on training observations."""
        # Calculate training medians to prevent leakage into imputation
        if "outdoor_temp_c" in X.columns and X["outdoor_temp_c"].notna().any():
            self.median_outdoor_temp = float(X["outdoor_temp_c"].median())
        if "relative_humidity" in X.columns and X["relative_humidity"].notna().any():
            self.median_humidity = float(X["relative_humidity"].median())

        df_feat = self._engineer_features(X)
        X_matrix = df_feat[self.feature_names].values
        self.scaler.fit(X_matrix)
        self.is_fitted = True
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transform observations into scaled feature matrix."""
        if not self.is_fitted:
            raise RuntimeError("CampusEnergyPreprocessor must be fitted before calling transform.")
        df_feat = self._engineer_features(X)
        X_matrix = df_feat[self.feature_names].values
        return self.scaler.transform(X_matrix)

    def transform_single(self, observation: Dict[str, Any]) -> np.ndarray:
        """Transform a single observation dictionary for real-time API inference."""
        df = pd.DataFrame([observation])
        return self.transform(df)

    def save(self, filepath: str):
        """Serialize preprocessor to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: str) -> "CampusEnergyPreprocessor":
        """Load fitted preprocessor from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Preprocessor file not found at: {filepath}")
        return joblib.load(filepath)


def chronological_train_test_split(
    df: pd.DataFrame,
    test_ratio: float = 0.20
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split time-series data chronologically to strictly prevent future-data leakage."""
    if "timestamp" not in df.columns:
        raise ValueError("DataFrame must contain a 'timestamp' column for chronological split.")

    # Sort strictly by timestamp
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1.0 - test_ratio))

    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()

    return train_df, test_df


def chronological_train_val_test_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.10,
    test_ratio: float = 0.20
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split time-series data chronologically into train, validation, and test partitions.
    
    Guarantees strict chronological ordering with zero future-data leakage:
    max(train_timestamp) < min(val_timestamp) and max(val_timestamp) < min(test_timestamp).
    """
    if "timestamp" not in df.columns:
        raise ValueError("DataFrame must contain a 'timestamp' column for chronological split.")

    if not np.isclose(train_ratio + val_ratio + test_ratio, 1.0):
        raise ValueError("train_ratio + val_ratio + test_ratio must sum to 1.0")

    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df_sorted)
    train_end_idx = int(n * train_ratio)
    val_end_idx = int(n * (train_ratio + val_ratio))

    train_df = df_sorted.iloc[:train_end_idx].copy()
    val_df = df_sorted.iloc[train_end_idx:val_end_idx].copy()
    test_df = df_sorted.iloc[val_end_idx:].copy()

    return train_df, val_df, test_df

