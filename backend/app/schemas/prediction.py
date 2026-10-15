"""Pydantic schemas for Model Inferences, Predictions, and Evaluation Runs."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PredictionResponse(BaseModel):
    id: int
    reading_id: int
    building_id: int
    building_name: Optional[str] = None
    building_code: Optional[str] = None
    timestamp: Optional[datetime] = None
    actual_energy_kwh: Optional[float] = None
    predicted_energy_kwh: float
    residual_kwh: float
    deviation_pct: Optional[float] = None
    model_version_tag: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPredictionsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[PredictionResponse]


class ModelEvaluationRunResponse(BaseModel):
    id: int
    model_version_id: int
    dataset_name: str
    sample_count: int
    mae: float
    rmse: float
    r2_score: float
    test_period_start: datetime
    test_period_end: datetime
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelVersionResponse(BaseModel):
    id: int
    model_name: str
    algorithm: str
    version_tag: str
    file_path: str
    is_active: bool
    hyperparameters: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    trained_at: datetime
    evaluation_runs: List[ModelEvaluationRunResponse] = []

    model_config = ConfigDict(from_attributes=True)

