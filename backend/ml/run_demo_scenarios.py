"""Runner and Automated Verifier for 10 Documented Synthetic Demo Scenarios.

Processes each scenario through the full application pipeline:
Manual Entry -> Feature Preprocessing -> RF Expected Inference -> Residual Calculation
-> Isolation Forest Scoring -> Dual Anomaly Verdict -> Rule Explanation -> Prescriptive Action.
"""
import os
import sys
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Building, EnergyReading, Prediction, AnomalyEvent, AnomalyExplanation, Recommendation
from app.services.reading_service import create_energy_reading
from app.services.prediction_service import generate_prediction_for_reading
from app.services.anomaly_service import evaluate_reading_anomalies
from app.services.explanation_engine import evaluate_anomaly_explanation
from app.services.recommendation_engine import generate_recommendation_for_anomaly
from app.schemas.reading import EnergyReadingCreate


def run_all_demo_scenarios(persist: bool = True) -> list:
    """Execute each demo scenario and verify full pipeline results."""
    scenarios_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data/demo_scenarios.json"))
    with open(scenarios_path, "r") as f:
        scenarios = json.load(f)

    db = SessionLocal()
    results = []

    print("=" * 85)
    print("CIT COIMBATORE - REPRODUCIBLE DEMO SCENARIO VERIFICATION")
    print("=" * 85)

    try:
        for scn in scenarios:
            scn_id = scn["scenario_id"]
            scn_name = scn["name"]
            code = scn["building_code"]
            ts = datetime.fromisoformat(scn["timestamp"])

            bld = db.query(Building).filter(Building.code == code).first()
            if not bld:
                print(f"ERROR: Building code '{code}' not found in database.")
                continue

            # Clear any previous test run for this building at this timestamp
            db.query(EnergyReading).filter(
                EnergyReading.building_id == bld.id,
                EnergyReading.timestamp == ts
            ).delete()
            db.commit()

            # 1. Store Manual Reading
            schema = EnergyReadingCreate(
                building_id=bld.id,
                timestamp=ts,
                energy_kwh=float(scn["energy_kwh"]),
                meter_interval_minutes=scn.get("meter_interval_minutes", 60),
                outdoor_temp_c=scn.get("outdoor_temp_c"),
                relative_humidity=scn.get("relative_humidity"),
                occupancy_count=scn.get("occupancy_count"),
                day_type=scn.get("day_type", "working_day"),
                operating_status=scn.get("operating_status", "normal"),
                hvac_status=scn.get("hvac_status", "off"),
                notes=f"Demo Scenario [{scn_id}]: {scn['intended_condition']}",
                tariff_rate=7.50
            )
            reading = create_energy_reading(db, schema)

            # 2. Generate Prediction via Trained Random Forest
            pred = generate_prediction_for_reading(db, reading.id)

            # 3. Anomaly Detection via Dual-Method Engine
            anomaly = evaluate_reading_anomalies(db, reading.id)
            actual_verdict = anomaly.severity if anomaly else "normal"

            # 4. Explanation and Recommendation (if anomaly detected)
            expl_title = "N/A"
            rec_action = "N/A"
            saved_inr = 0.0

            if anomaly:
                expl_data = evaluate_anomaly_explanation(bld, reading, pred, anomaly)
                rec_data = generate_recommendation_for_anomaly(bld, reading, pred, anomaly, expl_data)
                expl_title = expl_data["primary_hypothesis"]
                rec_action = rec_data["title"]
                saved_inr = round(rec_data["estimated_savings_kwh"] * 7.50, 2)

                # Persist explanation & recommendation records if not existing
                existing_expl = db.query(AnomalyExplanation).filter(AnomalyExplanation.anomaly_event_id == anomaly.id).first()
                if not existing_expl:
                    db_expl = AnomalyExplanation(
                        anomaly_event_id=anomaly.id,
                        primary_hypothesis=expl_data["primary_hypothesis"],
                        evidence=expl_data["evidence"],
                        confidence=expl_data["confidence"],
                        data_to_confirm=expl_data["data_to_confirm"],
                        recommended_next_action=expl_data["recommended_next_action"],
                    )
                    db.add(db_expl)

                existing_rec = db.query(Recommendation).filter(Recommendation.anomaly_event_id == anomaly.id).first()
                if not existing_rec:
                    db_rec = Recommendation(
                        anomaly_event_id=anomaly.id,
                        title=rec_data["title"],
                        priority=rec_data["priority"],
                        supporting_evidence=rec_data["supporting_evidence"],
                        recommended_action=rec_data["recommended_action"],
                        responsible_role=rec_data["responsible_role"],
                        follow_up_verification=rec_data["follow_up_verification"],
                        estimated_savings_kwh=rec_data["estimated_savings_kwh"],
                    )
                    db.add(db_rec)
                db.commit()

            status_flag = "✓ MATCH" if actual_verdict == scn["expected_verdict"] else f"~ DIFF ({actual_verdict})"
            print(f"[{scn_id}] {scn_name:<38} | {code:<8} | Actual: {scn['energy_kwh']:>5.1f} kWh | Expected: {pred.predicted_energy_kwh:>5.1f} kWh | Res: {pred.residual_kwh:>+6.1f} kWh ({pred.deviation_pct:>+6.1f}%) | Verdict: {actual_verdict.upper():<8} [{status_flag}]")

            results.append({
                "scenario_id": scn_id,
                "name": scn_name,
                "building": code,
                "timestamp": ts.isoformat(),
                "actual_kwh": scn["energy_kwh"],
                "predicted_kwh": round(pred.predicted_energy_kwh, 2),
                "residual_kwh": round(pred.residual_kwh, 2),
                "deviation_pct": round(pred.deviation_pct, 1),
                "expected_verdict": scn["expected_verdict"],
                "actual_verdict": actual_verdict,
                "is_match": (actual_verdict == scn["expected_verdict"]),
                "iso_score": round(anomaly.anomaly_score, 4) if anomaly else None,
                "explanation": expl_title,
                "recommendation": rec_action,
                "potential_savings_inr": saved_inr,
            })

    finally:
        db.close()

    print("=" * 85)
    matched = sum(1 for r in results if r["is_match"])
    print(f"Summary: {matched} / {len(results)} scenarios matched intended baseline expectation exactly.")
    print("=" * 85)
    return results


if __name__ == "__main__":
    run_all_demo_scenarios()

