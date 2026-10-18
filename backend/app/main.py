"""CIT Energy Consumption & Anomaly Detection System - FastAPI Entrypoint.
"""
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI-Based Campus Energy Consumption & Anomaly Detection at CIT Coimbatore.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
def root_status():
    """Root metadata endpoint."""
    return {
        "system": settings.PROJECT_NAME,
        "status": "online",
        "campus": "Coimbatore Institute of Technology (CIT), Coimbatore",
        "documentation": "/docs",
        "api_v1": settings.API_V1_STR,
    }


@app.get(f"{settings.API_V1_STR}/health", tags=["Health"], status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """Health check verifying API responsiveness and database connectivity."""
    db_status = "connected"
    db_type = "postgresql" if "postgresql" in settings.effective_database_url else "sqlite"
    try:
        # Run lightweight test query
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if "error" not in db_status else "degraded",
        "database": {
            "type": db_type,
            "status": db_status,
        },
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "thresholds": {
            "warning": settings.ANOMALY_WARNING_THRESHOLD,
            "critical": settings.ANOMALY_CRITICAL_THRESHOLD,
        },
    }


# Register Modular API Routers
from app.api import buildings, readings, predictions, models, anomalies, recommendations, dashboard, settings as settings_api, sustainability

app.include_router(buildings.router, prefix=settings.API_V1_STR)
app.include_router(readings.router, prefix=settings.API_V1_STR)
app.include_router(predictions.router, prefix=settings.API_V1_STR)
app.include_router(models.router, prefix=settings.API_V1_STR)
app.include_router(anomalies.router, prefix=settings.API_V1_STR)
app.include_router(recommendations.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(settings_api.router, prefix=settings.API_V1_STR)
app.include_router(sustainability.router, prefix=settings.API_V1_STR)


