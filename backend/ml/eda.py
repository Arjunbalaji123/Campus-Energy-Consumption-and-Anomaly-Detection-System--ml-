"""Exploratory Data Analysis (EDA) and Quality Diagnostics for CIT Energy Data.

Computes distributions, correlations, diurnal consumption curves, and quality metrics.
Can be executed as a standalone script or imported by services.
"""
import os
import sys
import json
from typing import Dict, Any
import pandas as pd
import numpy as np

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Building, EnergyReading


def load_dataset(use_db: bool = True, synthetic_only: bool = True) -> pd.DataFrame:
    """Load energy dataset from database or CSV snapshot, guaranteeing explicit anomaly labels."""
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data/synthetic_campus_energy.csv"))

    df = None
    if use_db:
        db = SessionLocal()
        try:
            query = (
                db.query(
                    EnergyReading.id,
                    EnergyReading.timestamp,
                    EnergyReading.energy_kwh,
                    EnergyReading.outdoor_temp_c,
                    EnergyReading.relative_humidity,
                    EnergyReading.occupancy_count,
                    EnergyReading.day_type,
                    EnergyReading.operating_status,
                    EnergyReading.hvac_status,
                    EnergyReading.is_synthetic,
                    EnergyReading.notes,
                    Building.code.label("building_code"),
                    Building.name.label("building_name"),
                    Building.category.label("building_category"),
                    Building.floor_area_sqm,
                    Building.max_capacity,
                    Building.has_hvac,
                )
                .join(Building, EnergyReading.building_id == Building.id)
                .order_by(EnergyReading.timestamp.asc())
            )
            if synthetic_only:
                query = query.filter(EnergyReading.is_synthetic == True)

            df = pd.read_sql(query.statement, db.bind)
        finally:
            db.close()

    if df is None or df.empty:
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            if synthetic_only and "is_synthetic" in df.columns:
                df = df[df["is_synthetic"] == True].copy()
        else:
            raise FileNotFoundError("Neither database records nor synthetic_campus_energy.csv could be loaded.")

    # Ensure timestamp is datetime and sorted chronologically
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Ensure explicit anomaly ground-truth columns are present
    if "is_anomaly" not in df.columns:
        df["is_anomaly"] = df["notes"].fillna("").str.contains("INJECTED_ANOMALY", case=False)

    if "anomaly_type" not in df.columns:
        df["anomaly_type"] = "normal"
        df.loc[df["notes"].fillna("").str.contains("Weekend HVAC", case=False), "anomaly_type"] = "weekend_hvac_surge"
        df.loc[df["notes"].fillna("").str.contains("machinery|overnight", case=False), "anomaly_type"] = "night_standby_machinery"
        df.loc[df["notes"].fillna("").str.contains("meter failure", case=False), "anomaly_type"] = "meter_failure_drop"
        df.loc[df["notes"].fillna("").str.contains("thermal surge", case=False), "anomaly_type"] = "extreme_thermal_surge"

    return df


def run_eda(save_summary: bool = True) -> Dict[str, Any]:
    """Execute comprehensive exploratory data analysis and return structured metrics."""
    df = load_dataset()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    total_records = len(df)
    buildings = df["building_code"].unique().tolist()
    date_min = df["timestamp"].min().isoformat()
    date_max = df["timestamp"].max().isoformat()

    # 1. Missingness & Quality
    missing_pct = (df.isnull().sum() / total_records * 100).round(2).to_dict()

    # 2. Building Consumption Statistics
    building_stats = {}
    for b_code in buildings:
        b_df = df[df["building_code"] == b_code]["energy_kwh"]
        building_stats[b_code] = {
            "mean_kwh": round(float(b_df.mean()), 2),
            "std_kwh": round(float(b_df.std()), 2),
            "median_kwh": round(float(b_df.median()), 2),
            "min_kwh": round(float(b_df.min()), 2),
            "max_kwh": round(float(b_df.max()), 2),
        }

    # 3. Operational State Analysis
    day_type_stats = (
        df.groupby("day_type")["energy_kwh"]
        .agg(["mean", "median", "count"])
        .round(2)
        .to_dict(orient="index")
    )

    # 4. Correlation Analysis
    corr_cols = ["energy_kwh", "outdoor_temp_c", "occupancy_count", "floor_area_sqm"]
    available_corr_cols = [c for c in corr_cols if c in df.columns]
    correlations = df[available_corr_cols].corr()["energy_kwh"].round(3).to_dict()

    # 5. Injected Anomalies Identification
    anomaly_rows = df[df["notes"].str.contains("INJECTED_ANOMALY", na=False)]
    anomaly_summary = []
    for _, row in anomaly_rows.iterrows():
        b_median = building_stats[row["building_code"]]["median_kwh"]
        deviation = round(row["energy_kwh"] - b_median, 2)
        dev_pct = round((deviation / b_median) * 100, 1)
        anomaly_summary.append({
            "timestamp": row["timestamp"].isoformat(),
            "building_code": row["building_code"],
            "energy_kwh": float(row["energy_kwh"]),
            "building_median_kwh": b_median,
            "deviation_kwh": deviation,
            "deviation_pct": dev_pct,
            "notes": str(row["notes"]),
        })

    summary = {
        "dataset_metrics": {
            "total_records": total_records,
            "building_count": len(buildings),
            "buildings": buildings,
            "start_time": date_min,
            "end_time": date_max,
        },
        "missing_values_percentage": missing_pct,
        "building_consumption_stats": building_stats,
        "day_type_breakdown": day_type_stats,
        "correlations_with_energy_kwh": correlations,
        "injected_anomalies_detected": anomaly_summary,
    }

    if save_summary:
        summary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data/eda_summary.json"))
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"EDA Summary successfully written to: {summary_path}")

    return summary


def print_eda_report():
    """Print clean formatted EDA terminal report."""
    summary = run_eda(save_summary=True)
    d = summary["dataset_metrics"]
    print("=" * 70)
    print("CIT COIMBATORE - CAMPUS ENERGY DATASET EXPLORATORY ANALYSIS")
    print("=" * 70)
    print(f"Total Observations : {d['total_records']} hourly readings")
    print(f"Campus Buildings   : {len(d['buildings'])} blocks ({', '.join(d['buildings'])})")
    print(f"Timespan           : {d['start_time']} to {d['end_time']}")
    print("-" * 70)
    print("BUILDING CONSUMPTION BENCHMARKS (kWh):")
    for b_code, s in summary["building_consumption_stats"].items():
        print(f"  • {b_code:<10} | Mean: {s['mean_kwh']:>6.1f} | Med: {s['median_kwh']:>6.1f} | Min: {s['min_kwh']:>5.1f} | Max: {s['max_kwh']:>6.1f}")
    print("-" * 70)
    print("FEATURE CORRELATION WITH ENERGY CONSUMPTION (kWh):")
    for feat, corr in summary["correlations_with_energy_kwh"].items():
        print(f"  • {feat:<20}: r = {corr:+.3f}")
    print("-" * 70)
    print(f"INJECTED ANOMALIES VERIFIED ({len(summary['injected_anomalies_detected'])} cases):")
    for a in summary["injected_anomalies_detected"]:
        print(f"  • [{a['building_code']}] {a['timestamp']} => {a['energy_kwh']} kWh (Dev: {a['deviation_pct']:+.1f}% vs median) | {a['notes'][:50]}...")
    print("=" * 70)


if __name__ == "__main__":
    print_eda_report()

