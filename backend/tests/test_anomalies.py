"""Integration and Unit Tests for Dual-Method Anomaly Detection and APIs."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import EnergyReading, AnomalyEvent
from app.services.anomaly_service import (
    evaluate_reading_anomalies,
    batch_scan_energy_readings,
    load_active_isolation_detector
)

client = TestClient(app)


def test_isolation_forest_detector_loads():
    """Verify Isolation Forest detector is loadable and ready for inference."""
    detector = load_active_isolation_detector()
    assert detector is not None
    assert "model" in detector
    assert "scaler" in detector
    assert "features" in detector


def test_dual_anomaly_detection_on_injected_cases():
    """Verify dual-method detection correctly identifies injected ground-truth anomalies."""
    db = SessionLocal()
    try:
        # 1. Injected IT Block Weekend Surge (168.5 kWh)
        it_surge = (
            db.query(EnergyReading)
            .filter(EnergyReading.notes.like("%Weekend HVAC%"))
            .first()
        )
        assert it_surge is not None
        event_it = evaluate_reading_anomalies(db, it_surge.id)
        assert event_it is not None
        assert event_it.severity == "critical"
        assert event_it.detection_method in ["dual", "residual"]

        # 2. Injected Workshop Meter Drop (2.1 kWh)
        work_drop = (
            db.query(EnergyReading)
            .filter(EnergyReading.notes.like("%meter failure%"))
            .first()
        )
        assert work_drop is not None
        event_work = evaluate_reading_anomalies(db, work_drop.id)
        assert event_work is not None
        assert event_work.severity == "critical"

        # 3. Normal Reading should not produce an anomaly
        normal_reading = (
            db.query(EnergyReading)
            .filter(EnergyReading.notes.is_(None))
            .filter(EnergyReading.operating_status == "normal")
            .filter(EnergyReading.day_type == "working_day")
            .first()
        )
        if normal_reading:
            event_norm = evaluate_reading_anomalies(db, normal_reading.id)
            # Either None or normal severity
            if event_norm:
                assert event_norm.severity in ["normal", "warning"]

    finally:
        db.close()


def test_batch_scan_service_and_api():
    """Verify batch scanning populates anomaly center."""
    response = client.post("/api/anomalies/batch-scan?limit=500")
    assert response.status_code == 200
    data = response.json()
    assert data["total_scanned"] > 0
    assert data["anomalies_detected"] > 0
    assert "critical_count" in data


def test_list_anomalies_api_and_filtering():
    """Verify GET /api/anomalies endpoint with pagination and severity filter."""
    response = client.get("/api/anomalies?page=1&page_size=10&severity=critical")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) <= 10

    if data["items"]:
        first = data["items"][0]
        assert first["severity"] == "critical"
        assert "building_name" in first
        assert "residual_kwh" in first
        assert "actual_energy_kwh" in first


def test_update_anomaly_investigation_status():
    """Verify updating anomaly workflow status via PUT /api/anomalies/{id}/status."""
    db = SessionLocal()
    try:
        anomaly = db.query(AnomalyEvent).first()
        if not anomaly:
            reading = db.query(EnergyReading).first()
            anomaly = AnomalyEvent(
                reading_id=reading.id,
                detection_method="residual",
                severity="warning",
                status="open",
            )
            db.add(anomaly)
            db.commit()
            db.refresh(anomaly)
        anomaly_id = anomaly.id
    finally:
        db.close()

    # Update to 'investigating'
    res1 = client.put(f"/api/anomalies/{anomaly_id}/status", json={"status": "investigating"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "investigating"

    # Update to 'resolved'
    res2 = client.put(f"/api/anomalies/{anomaly_id}/status", json={"status": "resolved"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "resolved"

    # Reject invalid status
    res3 = client.put(f"/api/anomalies/{anomaly_id}/status", json={"status": "invalid_status_code"})
    assert res3.status_code == 422
