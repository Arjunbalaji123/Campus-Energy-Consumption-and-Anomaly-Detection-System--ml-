"""Tests for Dashboard Overview and Timeseries Analytics APIs."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_dashboard_overview():
    res = client.get("/api/dashboard/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_energy_kwh" in data
    assert "total_cost_inr" in data
    assert "building_consumption" in data
    assert len(data["building_consumption"]) > 0
    assert "anomaly_severity_breakdown" in data
    assert "model_status" in data


def test_get_dashboard_timeseries_analytics_default():
    res = client.get("/api/dashboard/timeseries")
    assert res.status_code == 200
    data = res.json()
    assert "timeseries" in data
    assert "diurnal_profile" in data
    assert len(data["timeseries"]) > 0
    assert len(data["diurnal_profile"]) == 24
    
    first_pt = data["timeseries"][0]
    assert "timestamp" in first_pt
    assert "energy_kwh" in first_pt
    assert "is_anomaly" in first_pt

    hour_pt = data["diurnal_profile"][0]
    assert hour_pt["hour"] == 0
    assert "working_day_avg" in hour_pt
    assert "weekend_avg" in hour_pt


def test_get_dashboard_timeseries_analytics_with_building():
    # Fetch buildings first
    b_res = client.get("/api/buildings")
    assert b_res.status_code == 200
    buildings = b_res.json()
    assert len(buildings) > 0
    target_id = buildings[0]["id"]

    res = client.get(f"/api/dashboard/timeseries?building_id={target_id}&limit=48")
    assert res.status_code == 200
    data = res.json()
    assert data["building_id"] == target_id
    assert len(data["timeseries"]) <= 48
    assert len(data["diurnal_profile"]) == 24

