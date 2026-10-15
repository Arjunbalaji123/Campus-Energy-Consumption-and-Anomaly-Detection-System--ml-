"""SQLAlchemy ORM models for Anomaly Events, Explanations, and Actionable Recommendations."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class AnomalyEvent(Base):
    """Energy anomalies detected via residual analysis, Isolation Forest, or both."""
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, index=True)
    reading_id = Column(Integer, ForeignKey("energy_readings.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True, index=True)

    detection_method = Column(String(50), nullable=False)  # 'residual', 'isolation_forest', 'dual'
    severity = Column(String(20), nullable=False, index=True)  # 'normal', 'warning', 'critical'
    anomaly_score = Column(Float, nullable=True)           # Isolation forest decision function or z-score
    status = Column(String(30), default="open", nullable=False, index=True)  # 'open', 'investigating', 'resolved', 'dismissed'
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    reading = relationship("EnergyReading", back_populates="anomaly_events")
    prediction = relationship("Prediction", back_populates="anomaly_events")
    explanations = relationship("AnomalyExplanation", back_populates="anomaly_event", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="anomaly_event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnomalyEvent(id={self.id}, reading_id={self.reading_id}, method='{self.detection_method}', severity='{self.severity}')>"


class AnomalyExplanation(Base):
    """Transparent rule-based causal hypotheses and observed evidence."""
    __tablename__ = "anomaly_explanations"

    id = Column(Integer, primary_key=True, index=True)
    anomaly_event_id = Column(Integer, ForeignKey("anomaly_events.id", ondelete="CASCADE"), nullable=False, index=True)

    primary_hypothesis = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False)               # Structured key-value facts (e.g. {occupancy: 2, hour: 23, temp: 28})
    confidence = Column(String(20), nullable=False)       # 'low', 'medium', 'high'
    data_to_confirm = Column(Text, nullable=True)         # Additional data that would verify the cause
    recommended_next_action = Column(Text, nullable=True) # Direct action hint
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    anomaly_event = relationship("AnomalyEvent", back_populates="explanations")

    def __repr__(self):
        return f"<AnomalyExplanation(id={self.id}, event_id={self.anomaly_event_id}, confidence='{self.confidence}')>"


class Recommendation(Base):
    """Actionable recommendations for facilities staff and campus managers."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    anomaly_event_id = Column(Integer, ForeignKey("anomaly_events.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    priority = Column(String(20), nullable=False, index=True)  # 'low', 'medium', 'high', 'critical'
    supporting_evidence = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    responsible_role = Column(String(100), default="Facilities Staff", nullable=False) # e.g. 'Energy Manager'
    follow_up_verification = Column(Text, nullable=True)
    status = Column(String(30), default="open", nullable=False, index=True)  # 'open', 'investigating', 'resolved', 'dismissed'
    estimated_savings_kwh = Column(Float, nullable=True)       # Documented estimate only
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    anomaly_event = relationship("AnomalyEvent", back_populates="recommendations")

    def __repr__(self):
        return f"<Recommendation(id={self.id}, event_id={self.anomaly_event_id}, priority='{self.priority}', status='{self.status}')>"

