"""Comprehensive End-to-End Integration Test for CIT Campus Energy System.

Tests the full lifecycle from Building Registration -> Manual Observation Entry ->
Prediction Inference -> Dual Anomaly Detection -> Evidence-Based Explanation ->
Actionable Recommendation -> Dashboard Overview Aggregations -> Workflow Resolution.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_campus_energy_lifecycle():
    """Verify complete end-to-end data and decision pipeline."""
    # -------------------------------------------------------------
    # 1. Register a New Campus Building
    # -------------------------------------------------------------
    building_payload = {
        "name": "CIT Postgraduate Research Block",
        "code": "CIT-PGRES",
        "category": "Academic Block",
        "floors": 4,
        "floor_area_sqm": 5800.0,
        "max_capacity": 600,
        "operating_hours": "08:30 - 18:00",
        "operating_days": "Mon - Fri",
        "has_hvac": True,
        "lighting_type": "Smart LED Sensors",
        "meter_identifier": "MTR-CIT-PGRES-01",
        "notes": "Houses advanced research labs and PhD workstations."
    }
    b_res = client.post("/api/buildings", json=building_payload)
    assert b_res.status_code in [201, 400]
    if b_res.status_code == 400:
        # If created by previous run, fetch it
        all_b = client.get("/api/buildings").json()
        building_id = next(b["id"] for b in all_b if b["code"] == "CIT-PGRES")
    else:
        building_id = b_res.json()["id"]

    assert building_id is not None

    # -------------------------------------------------------------
    # 2. Submit a Manual Energy Reading with a Deliberate Off-Hours Spike
    # -------------------------------------------------------------
    reading_payload = {
        "building_id": building_id,
        "timestamp": "2026-10-25T23:00:00", # Late night (23:00)
        "energy_kwh": 145.0,                # High surge (normal standby ~20 kWh)
        "meter_interval_minutes": 60,
        "outdoor_temp_c": 26.0,
        "relative_humidity": 65.0,
        "occupancy_count": 5,               # Minimal occupants (5 out of 600)
        "day_type": "working_day",
        "operating_status": "closed",
        "hvac_status": "on",
        "tariff_rate": 7.50,
        "data_source": "manual",
        "notes": "E2E Test: Midnight research block heavy load."
    }
    # First delete any existing reading at this timestamp if re-testing
    client.post("/api/readings", json=reading_payload)
    readings_list = client.get(f"/api/readings?building_id={building_id}&page=1&page_size=10").json()
    test_reading = next(r for r in readings_list["items"] if r["timestamp"].startswith("2026-10-25T23:00"))
    reading_id = test_reading["id"]
    assert reading_id is not None
    assert test_reading["is_synthetic"] is False

    # -------------------------------------------------------------
    # 3. Generate Machine Learning Prediction (Expected Consumption)
    # -------------------------------------------------------------
    pred_res = client.post(f"/api/predictions/generate/{reading_id}")
    assert pred_res.status_code in [200, 201]
    pred_data = pred_res.json()
    expected_kwh = pred_data["predicted_energy_kwh"]
    residual_kwh = pred_data["residual_kwh"]

    assert expected_kwh < 145.0        # Expected should be significantly lower
    assert residual_kwh > 50.0         # Positive excess
    assert pred_data["deviation_pct"] > 50.0

    # -------------------------------------------------------------
    # 4. Run Dual-Method Anomaly Detection
    # -------------------------------------------------------------
    detect_res = client.post(f"/api/anomalies/detect/{reading_id}")
    assert detect_res.status_code == 200
    anomaly_data = detect_res.json()
    assert anomaly_data is not None
    assert anomaly_data["severity"] == "critical"
    anomaly_id = anomaly_data["id"]

    # -------------------------------------------------------------
    # 5. Verify Explanation Generation
    # -------------------------------------------------------------
    anom_detail = client.get(f"/api/anomalies/{anomaly_id}").json()
    assert anom_detail["id"] == anomaly_id

    # Check that explanation and recommendation exist in DB
    recs_res = client.get(f"/api/recommendations?building_id={building_id}").json()
    assert recs_res["total"] >= 1
    rec_item = recs_res["items"][0]
    assert rec_item["priority"] in ["critical", "high"]
    assert rec_item["estimated_savings_kwh"] > 40.0
    rec_id = rec_item["id"]

    # -------------------------------------------------------------
    # 6. Verify Dashboard Overview Reflects the New Anomaly
    # -------------------------------------------------------------
    dash_res = client.get("/api/dashboard/overview")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_energy_kwh"] > 0
    assert dash_data["total_readings"] > 0
    assert dash_data["active_anomalies_count"] > 0
    assert len(dash_data["recent_alerts"]) > 0

    # -------------------------------------------------------------
    # 7. Update Workflow Status: Investigating -> Resolved
    # -------------------------------------------------------------
    stat1 = client.put(f"/api/recommendations/{rec_id}/status", json={"status": "investigating"})
    assert stat1.status_code == 200
    assert stat1.json()["status"] == "investigating"

    stat2 = client.put(f"/api/recommendations/{rec_id}/status", json={"status": "resolved"})
    assert stat2.status_code == 200
    assert stat2.json()["status"] == "resolved"


def test_system_settings_and_threshold_calibration():
    """Verify settings retrieval and threshold validation."""
    # 1. Get settings
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    s_data = get_res.json()
    assert "Winter / Mild Dry" in s_data["coimbatore_season_mapping"]
    assert "IT Block" in s_data["building_categories"]
    assert "expected_energy" in s_data["active_models"]

    # 2. Update valid thresholds
    valid_payload = {"warning_threshold": 0.20, "critical_threshold": 0.45}
    up_res = client.put("/api/settings/thresholds", json=valid_payload)
    assert up_res.status_code == 200
    assert up_res.json()["anomaly_thresholds"]["warning"] == 0.20
    assert up_res.json()["anomaly_thresholds"]["critical"] == 0.45

    # 3. Reject invalid threshold order (critical <= warning)
    invalid_payload = {"warning_threshold": 0.50, "critical_threshold": 0.30}
    bad_res = client.put("/api/settings/thresholds", json=invalid_payload)
    assert bad_res.status_code == 422

    # Reset back to standard prototype defaults
    client.put("/api/settings/thresholds", json={"warning_threshold": 0.25, "critical_threshold": 0.50})

