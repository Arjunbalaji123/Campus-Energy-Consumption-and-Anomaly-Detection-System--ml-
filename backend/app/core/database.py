"""CIT Energy System - Database Engine and Session Factory.

Supports PostgreSQL natively, with automatic fallback for local development.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Determine connection URL and connection arguments
db_url = settings.effective_database_url
connect_args = {}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Automatically verify connections are alive
    echo=settings.DEBUG and not db_url.startswith("sqlite"),  # Log SQL queries in dev if Postgres
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to provide a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

