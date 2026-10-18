"""Datetime utilities for timezone-aware UTC timestamps.

Avoids deprecated datetime.utcnow() in modern Python 3.12+ while ensuring
database compatibility with SQLite and PostgreSQL datetime columns.
"""
from datetime import datetime, timezone


def get_utc_now() -> datetime:
    """Return naive UTC timestamp for standard database persistence."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

