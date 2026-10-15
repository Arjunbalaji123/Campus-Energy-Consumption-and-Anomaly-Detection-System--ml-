"""Integration and Unit Tests for Anomaly Explanations and Actionable Recommendations."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import EnergyReading, AnomalyEvent, AnomalyExplanation, Recommendation
from app.services.anomaly_service import evaluate_reading_anomalies

client = TestClient(app)


def test_explanation_and_recommendation_for_night_surge():
    """Verify explanation and recommendation generated for off-hours night surge."""
    db = SessionLocal()
    try:
        lab_reading = (
            db.query(EnergyReading)
            .filter(EnergyReading.notes.like("%machinery active%"))
            .first()
        )
        assert lab_reading is not None

        # Run evaluation
        anomaly = evaluate_reading_anomalies(db, lab_reading.id)
        assert anomaly is not None

        # Verify explanation
        expl = db.query(AnomalyExplanation).filter(AnomalyExplanation.anomaly_event_id == anomaly.id).first()
        assert expl is not None
        assert "outside standard operating hours" in expl.primary_hypothesis
        assert "minimal occupant presence" in expl.primary_hypothesis
        assert expl.confidence in ["high", "medium"]
        assert "actual_energy_kwh" in expl.evidence
        assert "occupancy_ratio" in expl.evidence

        # Verify recommendation
        rec = db.query(Recommendation).filter(Recommendation.anomaly_event_id == anomaly.id).first()
        assert rec is not None
        assert "After-Hours Equipment" in rec.title or "HVAC" in rec.title
        assert rec.responsible_role in ["Facilities Staff", "Energy Manager"]
        assert rec.priority in ["critical", "high"]
        assert rec.estimated_savings_kwh is not None
        assert rec.estimated_savings_kwh > 20.0
    finally:
        db.close()


def test_explanation_for_daytime_occupancy_surge():
    """Verify explanation for daytime surge during active hours."""
    db = SessionLocal()
    try:
        it_reading = (
            db.query(EnergyReading)
            .filter(EnergyReading.notes.like("%Weekend HVAC%"))
            .first()
        )
        assert it_reading is not None

        anomaly = evaluate_reading_anomalies(db, it_reading.id)
        assert anomaly is not None

        expl = db.query(AnomalyExplanation).filter(AnomalyExplanation.anomaly_event_id == anomaly.id).first()
        assert expl is not None
        assert "active campus hours" in expl.primary_hypothesis or "normal occupancy" in expl.primary_hypothesis
    finally:
        db.close()


def test_explanation_and_recommendation_for_meter_drop():
    """Verify explanation and recommendation for workshop sudden meter drop."""
    db = SessionLocal()
    try:
        work_reading = (
            db.query(EnergyReading)
            .filter(EnergyReading.notes.like("%meter failure%"))
            .first()
        )
        assert work_reading is not None

        anomaly = evaluate_reading_anomalies(db, work_reading.id)
        assert anomaly is not None

        expl = db.query(AnomalyExplanation).filter(AnomalyExplanation.anomaly_event_id == anomaly.id).first()
        assert expl is not None
        assert "low energy consumption" in expl.primary_hypothesis or "breaker trip" in expl.primary_hypothesis
        assert expl.confidence == "high"

        rec = db.query(Recommendation).filter(Recommendation.anomaly_event_id == anomaly.id).first()
        assert rec is not None
        assert "Electrical" in rec.title or "Meter" in rec.title
        assert rec.responsible_role == "Electrical Engineer"
        assert rec.priority == "critical"
    finally:
        db.close()


def test_recommendations_api_pagination_and_filter():
    """Verify GET /api/recommendations endpoint returns paginated actionable list."""
    response = client.get("/api/recommendations?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) >= 1

    first = data["items"][0]
    assert "title" in first
    assert "responsible_role" in first
    assert "recommended_action" in first
    assert "follow_up_verification" in first


def test_update_recommendation_status_lifecycle():
    """Verify PUT /api/recommendations/{id}/status updates workflow."""
    db = SessionLocal()
    try:
        rec = db.query(Recommendation).first()
        assert rec is not None
        rec_id = rec.id
    finally:
        db.close()

    # Update to 'investigating'
    res1 = client.put(f"/api/recommendations/{rec_id}/status", json={"status": "investigating"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "investigating"

    # Update to 'resolved'
    res2 = client.put(f"/api/recommendations/{rec_id}/status", json={"status": "resolved"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "resolved"

    # Reject invalid status
    res3 = client.put(f"/api/recommendations/{rec_id}/status", json={"status": "invalid_code"})
    assert res3.status_code == 422
