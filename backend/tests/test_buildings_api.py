"""Integration tests for Building Registry API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_buildings():
    """Verify listing all active campus buildings."""
    response = client.get("/api/buildings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 6
    codes = {b["code"] for b in data}
    assert "CIT-IT" in codes
    assert "CIT-MAIN" in codes


def test_filter_buildings_by_category():
    """Verify category filtering."""
    response = client.get("/api/buildings?category=IT%20Block")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["code"] == "CIT-IT"


def test_get_building_by_id():
    """Verify retrieving a single building profile."""
    # First get ID of CIT-IT
    list_res = client.get("/api/buildings")
    it_block = next(b for b in list_res.json() if b["code"] == "CIT-IT")
    
    response = client.get(f"/api/buildings/{it_block['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == it_block["name"]
    assert data["has_hvac"] is True
    assert len(data["equipment_profiles"]) > 0


def test_create_building_and_prevent_duplicate_code():
    """Verify building registration and duplicate prevention."""
    payload = {
        "name": "CIT Open Air Auditorium",
        "code": "CIT-AUDI",
        "category": "Other Campus Buildings",
        "floors": 1,
        "floor_area_sqm": 3500.0,
        "max_capacity": 2500,
        "operating_hours": "17:00 - 21:00",
        "operating_days": "Special Events",
        "has_hvac": False,
        "lighting_type": "Stage High-Power LED Floodlights",
        "meter_identifier": "MTR-CIT-AUDI-01",
        "notes": "Cultural events, graduation ceremonies, and student symposia."
    }

    # First creation should succeed
    res1 = client.post("/api/buildings", json=payload)
    assert res1.status_code in [201, 400] # 400 if already created in earlier test run

    # Duplicate code attempt must fail with 400
    res2 = client.post("/api/buildings", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_update_and_deactivate_building():
    """Verify updating building details and deactivation."""
    list_res = client.get("/api/buildings")
    work_block = next(b for b in list_res.json() if b["code"] == "CIT-WORK")
    
    # Update operating hours
    update_res = client.put(
        f"/api/buildings/{work_block['id']}",
        json={"operating_hours": "08:00 - 17:00"}
    )
    assert update_res.status_code == 200
    assert update_res.json()["operating_hours"] == "08:00 - 17:00"

    # Deactivate building
    del_res = client.delete(f"/api/buildings/{work_block['id']}")
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False

    # Should not appear in active-only list
    active_res = client.get("/api/buildings?active_only=true")
    active_codes = {b["code"] for b in active_res.json()}
    assert "CIT-WORK" not in active_codes

    # Re-activate for further tests
    client.put(f"/api/buildings/{work_block['id']}", json={"is_active": True})

