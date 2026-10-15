"""Service layer implementing Dashboard Aggregations and Campus Overview Analytics."""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.building import Building
from app.models.reading import EnergyReading
from app.models.anomaly import AnomalyEvent
from app.models.ml import Prediction, ModelVersion
from app.schemas.dashboard import (
    DashboardOverviewResponse, BuildingEnergyStat, RecentAlertItem,
    TimeSeriesPoint, DiurnalPoint, DashboardAnalyticsResponse
)


def get_dashboard_overview_metrics(db: Session) -> DashboardOverviewResponse:
    """Compute high-level campus energy metrics, building breakdowns, and recent alerts."""
    # 1. Total Campus Consumption & Cost
    totals = db.query(
        func.count(EnergyReading.id).label("total_readings"),
        func.sum(EnergyReading.energy_kwh).label("total_kwh"),
        func.sum(EnergyReading.energy_kwh * func.coalesce(EnergyReading.tariff_rate, 7.50)).label("total_cost"),
    ).first()

    total_readings = totals.total_readings or 0
    total_kwh = round(float(totals.total_kwh or 0.0), 2)
    total_cost = round(float(totals.total_cost or 0.0), 2)

    total_buildings = db.query(func.count(Building.id)).filter(Building.is_active.is_(True)).scalar() or 0

    # 2. Anomaly Breakdown
    sev_query = (
        db.query(AnomalyEvent.severity, func.count(AnomalyEvent.id))
        .group_by(AnomalyEvent.severity)
        .all()
    )
    severity_map = {"critical": 0, "warning": 0, "normal": 0}
    for sev, count in sev_query:
        if sev in severity_map:
            severity_map[sev] = count

    active_anomalies_count = (
        db.query(func.count(AnomalyEvent.id))
        .filter(AnomalyEvent.status.in_(["open", "investigating"]))
        .scalar() or 0
    )

    # 3. Building-Wise Consumption Benchmarks
    buildings = db.query(Building).filter(Building.is_active.is_(True)).all()
    building_stats = []

    for b in buildings:
        b_readings = db.query(
            func.count(EnergyReading.id).label("cnt"),
            func.sum(EnergyReading.energy_kwh).label("sum_kwh"),
            func.avg(EnergyReading.energy_kwh).label("avg_kwh"),
        ).filter(EnergyReading.building_id == b.id).first()

        b_anomalies = (
            db.query(func.count(AnomalyEvent.id))
            .join(EnergyReading, AnomalyEvent.reading_id == EnergyReading.id)
            .filter(EnergyReading.building_id == b.id)
            .scalar() or 0
        )

        b_kwh_sum = round(float(b_readings.sum_kwh or 0.0), 2)
        b_kwh_avg = round(float(b_readings.avg_kwh or 0.0), 2)

        building_stats.append(BuildingEnergyStat(
            building_id=b.id,
            building_name=b.name,
            building_code=b.code,
            building_category=b.category,
            total_energy_kwh=b_kwh_sum,
            avg_hourly_kwh=b_kwh_avg,
            reading_count=b_readings.cnt or 0,
            anomaly_count=b_anomalies,
        ))

    # 4. Recent Alerts (Latest 10)
    alerts_query = (
        db.query(AnomalyEvent)
        .join(EnergyReading, AnomalyEvent.reading_id == EnergyReading.id)
        .join(Building, EnergyReading.building_id == Building.id)
        .outerjoin(Prediction, AnomalyEvent.prediction_id == Prediction.id)
        .order_by(EnergyReading.timestamp.desc())
        .limit(10)
        .all()
    )

    recent_alerts = []
    for a in alerts_query:
        r = a.reading
        p = a.prediction
        b = r.building if r else None

        recent_alerts.append(RecentAlertItem(
            anomaly_id=a.id,
            reading_id=a.reading_id,
            building_name=b.name if b else "Unknown",
            building_code=b.code if b else "N/A",
            timestamp=r.timestamp if r else a.detected_at,
            actual_energy_kwh=r.energy_kwh if r else 0.0,
            predicted_energy_kwh=p.predicted_energy_kwh if p else None,
            residual_kwh=p.residual_kwh if p else None,
            deviation_pct=p.deviation_pct if p else None,
            severity=a.severity,
            detection_method=a.detection_method,
            status=a.status,
        ))

    # 5. Model Status Info
    rf_model = db.query(ModelVersion).filter(ModelVersion.version_tag == "rf_expected_v1").first()
    iso_model = db.query(ModelVersion).filter(ModelVersion.version_tag == "iso_forest_v1").first()

    model_status = {
        "random_forest": {
            "version": rf_model.version_tag if rf_model else "Not trained",
            "is_active": rf_model.is_active if rf_model else False,
            "test_r2": rf_model.metrics.get("test", {}).get("r2") if (rf_model and rf_model.metrics) else None,
        },
        "isolation_forest": {
            "version": iso_model.version_tag if iso_model else "Not trained",
            "is_active": iso_model.is_active if iso_model else False,
            "outlier_pct": iso_model.metrics.get("outlier_pct") if (iso_model and iso_model.metrics) else None,
        }
    }

    return DashboardOverviewResponse(
        total_energy_kwh=total_kwh,
        total_cost_inr=total_cost,
        total_readings=total_readings,
        total_buildings=total_buildings,
        active_anomalies_count=active_anomalies_count,
        anomaly_severity_breakdown=severity_map,
        building_consumption=building_stats,
        recent_alerts=recent_alerts,
        model_status=model_status,
        server_time=datetime.now(timezone.utc),
    )


def get_dashboard_timeseries_analytics(
    db: Session,
    building_id: Optional[int] = None,
    limit: int = 168
) -> DashboardAnalyticsResponse:
    """Retrieve chronological actual vs expected energy consumption time series and 24h diurnal profiles."""
    # Default to first active building if none provided
    if building_id is None:
        first_b = db.query(Building).filter(Building.is_active.is_(True)).order_by(Building.id).first()
        if first_b:
            building_id = first_b.id

    building = db.query(Building).filter(Building.id == building_id).first() if building_id else None

    # Fetch chronological readings with linked predictions and anomalies
    query = (
        db.query(EnergyReading, Prediction, AnomalyEvent)
        .outerjoin(Prediction, Prediction.reading_id == EnergyReading.id)
        .outerjoin(AnomalyEvent, AnomalyEvent.reading_id == EnergyReading.id)
    )

    if building_id:
        query = query.filter(EnergyReading.building_id == building_id)

    rows = query.order_by(EnergyReading.timestamp.desc()).limit(limit).all()
    rows.reverse()

    timeseries = []
    for r, p, a in rows:
        timeseries.append(
            TimeSeriesPoint(
                timestamp=r.timestamp,
                energy_kwh=round(float(r.energy_kwh), 2),
                predicted_kwh=round(float(p.predicted_energy_kwh), 2) if p and p.predicted_energy_kwh is not None else None,
                residual_kwh=round(float(p.residual_kwh), 2) if p and p.residual_kwh is not None else None,
                is_anomaly=(a is not None),
                severity=a.severity if a else None,
            )
        )

    # Compute 24-hour diurnal profile (Working Day vs Non-Working Day)
    diurnal_query = db.query(EnergyReading)
    if building_id:
        diurnal_query = diurnal_query.filter(EnergyReading.building_id == building_id)

    all_readings = diurnal_query.all()
    work_by_hour: Dict[int, List[float]] = {h: [] for h in range(24)}
    nonwork_by_hour: Dict[int, List[float]] = {h: [] for h in range(24)}

    for r in all_readings:
        h = r.timestamp.hour
        if r.day_type == "working_day":
            work_by_hour[h].append(r.energy_kwh)
        else:
            nonwork_by_hour[h].append(r.energy_kwh)

    diurnal_profile = []
    for h in range(24):
        work_vals = work_by_hour[h]
        nonwork_vals = nonwork_by_hour[h]
        work_avg = round(float(sum(work_vals) / len(work_vals)), 2) if work_vals else 0.0
        nonwork_avg = round(float(sum(nonwork_vals) / len(nonwork_vals)), 2) if nonwork_vals else 0.0

        diurnal_profile.append(
            DiurnalPoint(
                hour=h,
                working_day_avg=work_avg,
                weekend_avg=nonwork_avg,
            )
        )

    return DashboardAnalyticsResponse(
        building_id=building.id if building else None,
        building_name=building.name if building else "All Campus Buildings",
        building_code=building.code if building else "CIT",
        timeseries=timeseries,
        diurnal_profile=diurnal_profile,
    )
