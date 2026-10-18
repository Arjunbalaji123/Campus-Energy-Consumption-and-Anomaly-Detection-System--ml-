"""SQLAlchemy ORM models for Campus Sustainability Intelligence Module.

Provides entities for grid emission factor configuration, institutional sustainability
targets, and empirical recommendation savings verification.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class SustainabilityConfig(Base):
    """Configurable sustainability parameters including regional grid emissions factor."""
    __tablename__ = "sustainability_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False, default="kg CO2e/kWh")
    source_name = Column(String(250), nullable=False)
    effective_date = Column(String(50), nullable=False)
    applicable_region = Column(String(150), nullable=False)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SustainabilityConfig(key='{self.config_key}', val={self.config_value} {self.unit})>"


class SustainabilityTarget(Base):
    """Institutional campus decarbonization and energy efficiency target."""
    __tablename__ = "sustainability_targets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Scope: Null building_id implies Campus-Wide scope
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Target Specification
    metric_type = Column(String(50), default="electricity_kwh", nullable=False)  # 'electricity_kwh', 'carbon_emissions_kg', 'energy_intensity_kwh_sqm'
    target_reduction_pct = Column(Float, nullable=False)  # e.g., 10.0 for 10% reduction
    
    # Baseline Specification
    baseline_period_start = Column(DateTime, nullable=False)
    baseline_period_end = Column(DateTime, nullable=False)
    baseline_value = Column(Float, nullable=False)  # Baseline consumption in metric unit
    
    # Timeline & Progress
    target_completion_date = Column(DateTime, nullable=False)
    current_measured_progress_pct = Column(Float, default=0.0, nullable=False)
    current_measured_value = Column(Float, nullable=True)
    status = Column(String(30), default="in_progress", nullable=False, index=True)  # 'in_progress', 'achieved', 'at_risk', 'expired'
    last_calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    building = relationship("Building")

    def __repr__(self):
        return f"<SustainabilityTarget(id={self.id}, name='{self.name}', target={self.target_reduction_pct}%, status='{self.status}')>"


class SustainabilityVerification(Base):
    """Empirical audit ledger verifying real post-action energy and carbon reductions."""
    __tablename__ = "sustainability_verifications"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Baseline comparison window
    baseline_period_start = Column(DateTime, nullable=False)
    baseline_period_end = Column(DateTime, nullable=False)
    baseline_avg_kwh = Column(Float, nullable=False)
    
    # Post-action verification window
    post_action_period_start = Column(DateTime, nullable=False)
    post_action_period_end = Column(DateTime, nullable=False)
    post_action_avg_kwh = Column(Float, nullable=False)
    
    # Measured Reductions
    observed_reduction_kwh = Column(Float, nullable=False)
    observed_reduction_pct = Column(Float, nullable=False)
    cost_savings_inr = Column(Float, nullable=False)
    emissions_reduction_kg_co2e = Column(Float, nullable=False)
    
    # Audit Status
    verification_status = Column(String(30), default="pending", nullable=False, index=True)  # 'verified', 'pending', 'insufficient_data', 'reverted'
    verification_criteria = Column(Text, nullable=False)
    verified_by = Column(String(100), default="Automated Telemetry Audit", nullable=False)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    recommendation = relationship("Recommendation")

    def __repr__(self):
        return f"<SustainabilityVerification(id={self.id}, rec_id={self.recommendation_id}, status='{self.verification_status}')>"

