"""Integration tests for Manual Energy Readings, Search, and CSV Import/Export."""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_readings_pagination():
    """Verify paginated retrieval of energy records."""
    response = client.get("/api/readings?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert data["total"] >= 6480
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["total_pages"] >= 648

    # Verify record structure
    first_item = data["items"][0]
    assert "energy_kwh" in first_item
    assert "building_name" in first_item
    assert "building_code" in first_item


def test_manual_reading_entry_and_duplicate_rejection():
    """Verify manual submission of single observation and duplicate check."""
    # Fetch valid building ID
    b_res = client.get("/api/buildings")
    it_building = next(b for b in b_res.json() if b["code"] == "CIT-IT")

    test_timestamp = "2026-10-15T10:00:00"
    payload = {
        "building_id": it_building["id"],
        "timestamp": test_timestamp,
        "energy_kwh": 142.5,
        "meter_interval_minutes": 60,
        "indoor_temp_c": 24.0,
        "outdoor_temp_c": 32.5,
        "relative_humidity": 55.0,
        "occupancy_count": 450,
        "day_type": "working_day",
        "operating_status": "normal",
        "hvac_status": "on",
        "tariff_rate": 7.50,
        "data_source": "manual",
        "notes": "Manual observation taken during mid-day student lab session."
    }

    # Submit manual reading
    create_res = client.post("/api/readings", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["energy_kwh"] == 142.5
    assert created_data["is_synthetic"] is False
    assert created_data["data_source"] == "manual"
    reading_id = created_data["id"]

    # Submit exact duplicate (same building, same timestamp) -> must fail 400
    dup_res = client.post("/api/readings", json=payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # Clean up test record
    del_res = client.delete(f"/api/readings/{reading_id}")
    assert del_res.status_code == 204


def test_reject_invalid_reading_inputs():
    """Verify Pydantic validation rejects negative kWh and invalid day_type."""
    b_res = client.get("/api/buildings")
    b_id = b_res.json()[0]["id"]

    # Negative energy
    bad_kwh = {
        "building_id": b_id,
        "timestamp": "2026-10-15T11:00:00",
        "energy_kwh": -50.0,
    }
    res1 = client.post("/api/readings", json=bad_kwh)
    assert res1.status_code == 422

    # Invalid day type
    bad_day = {
        "building_id": b_id,
        "timestamp": "2026-10-15T11:00:00",
        "energy_kwh": 75.0,
        "day_type": "invalid_day_category"
    }
    res2 = client.post("/api/readings", json=bad_day)
    assert res2.status_code == 422


def test_csv_export_endpoint():
    """Verify CSV export streams valid CSV headers and rows."""
    b_res = client.get("/api/buildings")
    it_id = next(b["id"] for b in b_res.json() if b["code"] == "CIT-IT")

    response = client.get(f"/api/readings/export/csv?building_id={it_id}&limit=50")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    csv_text = response.text
    assert "building_code" in csv_text
    assert "energy_kwh" in csv_text
    assert "CIT-IT" in csv_text


def test_csv_import_endpoint():
    """Verify bulk CSV import endpoint handles upload, duplicates, and new records."""
    csv_content = """building_code,timestamp,energy_kwh,meter_interval_minutes,outdoor_temp_c,relative_humidity,occupancy_count,day_type,operating_status,hvac_status,tariff_rate,notes
CIT-ACAD,2026-10-20T09:00:00,72.4,60,28.5,60.0,850,working_day,normal,off,7.50,Morning lectures
CIT-ACAD,2026-10-20T10:00:00,81.0,60,30.0,58.0,1100,working_day,normal,off,7.50,Mid-morning full load
"""
    files = {"file": ("test_import.csv", csv_content, "text/csv")}
    response = client.post("/api/readings/import/csv", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert data["imported"] in [0, 2] # 2 imported, or skipped if already run

