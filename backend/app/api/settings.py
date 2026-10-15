"""FastAPI router for System Settings, Season Mappings, and Thresholds."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.ml import ModelVersion
from app.schemas.settings import SystemSettingsResponse, ThresholdUpdateRequest

router = APIRouter(prefix="/settings", tags=["Settings"])

BUILDING_CATEGORIES = [
    "Main Block",
    "IT Block",
    "Academic Block",
    "Laboratory Block",
    "Library",
    "Administration Block",
    "Workshop / Equipment Block",
    "Other Campus Buildings"
]

COIMBATORE_SEASON_MAPPING = {
    "Winter / Mild Dry": {"months": [12, 1, 2], "temp_range": "19°C - 30°C", "humidity": "Low to Moderate"},
    "Summer / Hot Pre-Monsoon": {"months": [3, 4, 5], "temp_range": "24°C - 38°C", "humidity": "Moderate with peak heat"},
    "South-West Monsoon": {"months": [6, 7, 8], "temp_range": "22°C - 31°C", "humidity": "High with seasonal rains"},
    "North-East Monsoon / Post-Monsoon": {"months": [9, 10, 11], "temp_range": "22°C - 30°C", "humidity": "Elevated with peak rainfall"},
}


@router.get("", response_model=SystemSettingsResponse)
def get_system_settings(db: Session = Depends(get_db)):
    """Retrieve configurable anomaly thresholds, building categories, and season mappings."""
    rf_model = db.query(ModelVersion).filter(ModelVersion.version_tag == "rf_expected_v1").first()
    iso_model = db.query(ModelVersion).filter(ModelVersion.version_tag == "iso_forest_v1").first()

    return SystemSettingsResponse(
        project_name=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        api_version="1.0.0",
        anomaly_thresholds={
            "warning": settings.ANOMALY_WARNING_THRESHOLD,
            "critical": settings.ANOMALY_CRITICAL_THRESHOLD,
        },
        building_categories=BUILDING_CATEGORIES,
        coimbatore_season_mapping=COIMBATORE_SEASON_MAPPING,
        active_models={
            "expected_energy": rf_model.version_tag if rf_model else "Not active",
            "outlier_detector": iso_model.version_tag if iso_model else "Not active",
        }
    )


@router.put("/thresholds", response_model=SystemSettingsResponse)
def update_thresholds(
    body: ThresholdUpdateRequest,
    db: Session = Depends(get_db)
):
    """Calibrate anomaly deviation warning and critical thresholds."""
    settings.ANOMALY_WARNING_THRESHOLD = body.warning_threshold
    settings.ANOMALY_CRITICAL_THRESHOLD = body.critical_threshold
    return get_system_settings(db)

