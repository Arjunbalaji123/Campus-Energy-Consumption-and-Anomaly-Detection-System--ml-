"""Tests for application configuration and environment settings."""
import os
import pytest
from app.core.config import Settings


def test_default_settings():
    """Verify default settings values when initialized."""
    config = Settings()
    assert "CIT" in config.PROJECT_NAME
    assert config.API_V1_STR == "/api"
    assert config.ANOMALY_WARNING_THRESHOLD == 0.25
    assert config.ANOMALY_CRITICAL_THRESHOLD == 0.50


def test_cors_origins_parsing():
    """Verify comma-separated origins parse into a list."""
    config = Settings(ALLOWED_ORIGINS="http://localhost:3000, http://cit.edu")
    assert "http://localhost:3000" in config.cors_origins
    assert "http://cit.edu" in config.cors_origins


def test_database_url_fallback():
    """Verify that SQLite fallback behaves as expected when enabled."""
    config = Settings(USE_SQLITE_FALLBACK=True, DATABASE_URL="sqlite:///./test.db")
    assert config.effective_database_url.startswith("sqlite")

