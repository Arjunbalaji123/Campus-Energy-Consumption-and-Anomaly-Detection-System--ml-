"""Tests for Campus Sustainability Intelligence Module APIs and Business Logic."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.sustainability import SustainabilityConfig, SustainabilityTarget, SustainabilityVerification
from app.models.anomaly import Recommendation

client = TestClient(app)


def test_get_sustainability_summary():
    """Verify /api/sustainability/summary returns valid campus sustainability KPIs."""
    res = client.get("/api/sustainability/summary")
    assert res.status_code == 200
    data = res.json()

    assert "total_energy_kwh" in data
    assert "total_emissions_kg_co2e" in data
    assert "total_emissions_tonnes_co2e" in data
    assert "average_energy_intensity_kwh_sqm" in data
    assert "emissions_factor_info" in data
    assert "is_synthetic_notice" in data

    assert data["total_energy_kwh"] > 0.0
    assert data["total_emissions_kg_co2e"] > 0.0
    assert data["total_emissions_tonnes_co2e"] > 0.0
    assert data["average_energy_intensity_kwh_sqm"] > 0.0

    factor_info = data["emissions_factor_info"]
    assert factor_info["emission_factor"] > 0.0
    assert "kg CO2e/kWh" in factor_info["unit"]
    assert "CEA" in factor_info["source_name"] or "Central Electricity Authority" in factor_info["source_name"]


def test_emissions_calculation_accuracy():
    """Verify emissions formula: Emissions = Electricity (kWh) * Grid Factor (kg CO2e/kWh)."""
    res = client.get("/api/sustainability/summary")
    assert res.status_code == 200
    data = res.json()

    total_kwh = data["total_energy_kwh"]
    factor = data["emissions_factor_info"]["emission_factor"]
    expected_emissions_kg = round(total_kwh * factor, 2)
    expected_emissions_tonnes = round(expected_emissions_kg / 1000.0, 3)

    assert abs(data["total_emissions_kg_co2e"] - expected_emissions_kg) < 0.05
    assert abs(data["total_emissions_tonnes_co2e"] - expected_emissions_tonnes) < 0.005


def test_building_sustainability_rankings():
    """Verify building sustainability ranking and intensity normalization."""
    res = client.get("/api/sustainability/buildings")
    assert res.status_code == 200
    buildings = res.json()
    assert len(buildings) > 0

    first = buildings[0]
    assert "building_id" in first
    assert "name" in first
    assert "code" in first
    assert "energy_intensity_kwh_sqm" in first
    assert "emissions_kg_co2e" in first
    assert "baseline_expected_kwh" in first

    # Ensure list is sorted descending by energy intensity
    intensities = [b["energy_intensity_kwh_sqm"] for b in buildings]
    assert intensities == sorted(intensities, reverse=True)


def test_sustainability_trends_daily_and_hourly():
    """Verify timeseries trends endpoint supporting daily and hourly granularity."""
    # Daily granularity
    res_daily = client.get("/api/sustainability/trends?granularity=daily")
    assert res_daily.status_code == 200
    data_daily = res_daily.json()
    assert data_daily["granularity"] == "daily"
    assert len(data_daily["trends"]) > 0

    point = data_daily["trends"][0]
    assert "timestamp" in point
    assert "actual_kwh" in point
    assert "baseline_kwh" in point
    assert "emissions_kg_co2e" in point
    assert "energy_intensity_kwh_sqm" in point

    # Hourly granularity
    res_hourly = client.get("/api/sustainability/trends?granularity=hourly")
    assert res_hourly.status_code == 200
    assert res_hourly.json()["granularity"] == "hourly"


def test_carbon_footprint_analysis_and_equivalencies():
    """Verify Scope 2 carbon footprint analysis and environmental equivalencies."""
    res = client.get("/api/sustainability/emissions")
    assert res.status_code == 200
    data = res.json()

    assert "scope_boundary_notice" in data
    assert "Scope 2" in data["scope_boundary_notice"]
    assert "Scope 1" in data["scope_boundary_notice"]
    assert "total_emissions_kg_co2e" in data
    assert "building_breakdown" in data
    assert "equivalencies" in data

    eq = data["equivalencies"]
    assert "tree_seedlings_10_years" in eq
    assert "passenger_vehicle_km_avoided" in eq
    assert eq["tree_seedlings_10_years"] > 0
    assert eq["passenger_vehicle_km_avoided"] > 0


def test_emission_factor_get_and_update():
    """Verify configuration endpoint for grid emissions factor."""
    # Get active factor
    res_get = client.get("/api/sustainability/factor")
    assert res_get.status_code == 200
    orig = res_get.json()
    assert orig["emission_factor"] > 0

    # Update factor to test calibration
    res_update = client.put("/api/sustainability/factor", json={
        "emission_factor": 0.725,
        "source_name": "CEA India Updated Baseline Test",
        "effective_date": "2025-2026",
        "applicable_region": "Southern Regional Grid"
    })
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["emission_factor"] == 0.725
    assert updated["source_name"] == "CEA India Updated Baseline Test"

    # Revert to standard default
    client.put("/api/sustainability/factor", json={
        "emission_factor": 0.716,
        "source_name": "Central Electricity Authority (CEA) of India, CO2 Baseline Database v19",
        "effective_date": "2024-2025",
        "applicable_region": "Southern Regional Grid (Tamil Nadu / Coimbatore)"
    })


from app.core.datetime_utils import get_utc_now


def test_sustainability_targets_lifecycle():
    """Verify target registration and progress retrieval."""
    now = get_utc_now()
    target_payload = {
        "name": "CIT Solar Rooftop Offset 2026",
        "description": "Offsetting daytime laboratory baseline consumption via rooftop PV integration.",
        "building_id": None,
        "metric_type": "electricity_kwh",
        "target_reduction_pct": 12.0,
        "baseline_period_start": (now - timedelta(days=30)).isoformat(),
        "baseline_period_end": (now - timedelta(days=10)).isoformat(),
        "baseline_value": 75000.0,
        "target_completion_date": (now + timedelta(days=90)).isoformat()
    }

    create_res = client.post("/api/sustainability/targets", json=target_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["name"] == "CIT Solar Rooftop Offset 2026"
    assert created["target_reduction_pct"] == 12.0
    assert created["status"] in ["in_progress", "achieved", "at_risk"]

    # Retrieve all targets
    list_res = client.get("/api/sustainability/targets")
    assert list_res.status_code == 200
    targets = list_res.json()
    assert any(t["id"] == created["id"] for t in targets)


def test_savings_verification_insufficient_data_guard():
    """Verify verification engine handles insufficient data without false positive verification."""
    db = SessionLocal()
    rec = db.query(Recommendation).first()
    db.close()
    assert rec is not None

    now = get_utc_now()
    # Window with zero readings (future dates)
    future_payload = {
        "recommendation_id": rec.id,
        "baseline_period_start": (now + timedelta(days=10)).isoformat(),
        "baseline_period_end": (now + timedelta(days=12)).isoformat(),
        "post_action_period_start": (now + timedelta(days=13)).isoformat(),
        "post_action_period_end": (now + timedelta(days=15)).isoformat(),
        "notes": "Test future window with no data"
    }

    res = client.post(f"/api/sustainability/verify/{rec.id}", json=future_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verification_status"] == "insufficient_data"
    assert data["observed_reduction_kwh"] == 0.0


def test_sustainability_report_generation():
    """Verify full institutional sustainability report endpoint."""
    res = client.get("/api/sustainability/report")
    assert res.status_code == 200
    report = res.json()

    assert "report_title" in report
    assert "data_provenance_disclaimer" in report
    assert "DATA PROVENANCE NOTICE" in report["data_provenance_disclaimer"]
    assert "summary_metrics" in report
    assert "building_benchmarks" in report
    assert "targets_status" in report
    assert "verified_savings_ledger" in report
    assert "methodology_notes" in report
    assert len(report["methodology_notes"]) >= 3


def test_sustainability_settings_and_recommendations_endpoints():
    """Verify /settings alias and /recommendations sustainability endpoint."""
    # 1. Test /sustainability/settings GET
    res_set = client.get("/api/sustainability/settings")
    assert res_set.status_code == 200
    assert "emission_factor" in res_set.json()

    # 2. Test /sustainability/recommendations GET
    res_rec = client.get("/api/sustainability/recommendations")
    assert res_rec.status_code == 200
    recs = res_rec.json()
    assert isinstance(recs, list)
    if len(recs) > 0:
        first = recs[0]
        assert "estimated_emissions_reduction_kg_co2e" in first
        assert "estimated_cost_reduction_inr" in first

