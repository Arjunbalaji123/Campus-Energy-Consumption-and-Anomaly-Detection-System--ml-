"""CIT Energy System - Core Application Configuration.

Loads environment variables with type validation and sensible defaults.
"""
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


import os

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DEFAULT_SQLITE_PATH = os.path.join(BACKEND_DIR, "cit_energy.db")


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "CIT Coimbatore Energy Anomaly Detection System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/cit_energy_db"
    SQLITE_FALLBACK_URL: str = f"sqlite:///{DEFAULT_SQLITE_PATH}"
    USE_SQLITE_FALLBACK: bool = True

    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Anomaly Thresholds
    ANOMALY_WARNING_THRESHOLD: float = 0.25
    ANOMALY_CRITICAL_THRESHOLD: float = 0.50

    # Paths
    MODEL_DIR: str = "./ml/saved_models"
    DATA_DIR: str = "./ml/data"

    @property
    def cors_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a clean list of URLs."""
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def effective_database_url(self) -> str:
        """Return the effective database URL, respecting the fallback flag and normalizing postgres dialect."""
        url = self.SQLITE_FALLBACK_URL if self.USE_SQLITE_FALLBACK else self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()

