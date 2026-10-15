"""Rule-Based Explainability Engine for CIT Campus Energy Anomalies.

Generates transparent, evidence-based causal hypotheses with documented confidence ratings
and supporting data requirements. Explanations represent verifiable hypotheses, not causal AI.
"""
from typing import Dict, Any, Tuple
from app.models.building import Building
from app.models.reading import EnergyReading
from app.models.ml import Prediction
from app.models.anomaly import AnomalyEvent, AnomalyExplanation


def evaluate_anomaly_explanation(
    building: Building,
    reading: EnergyReading,
    prediction: Prediction,
    anomaly: AnomalyEvent
) -> Dict[str, Any]:
    """Evaluate observed evidence against transparent heuristic operational rules.
    
    Returns a dictionary containing:
    - primary_hypothesis: str
    - evidence: dict
    - confidence: 'low', 'medium', 'high'
    - data_to_confirm: str
    - recommended_next_action: str
    """
    actual_kwh = float(reading.energy_kwh)
    pred_kwh = float(prediction.predicted_energy_kwh) if prediction else 0.0
    residual = float(prediction.residual_kwh) if prediction else 0.0
    dev_pct = float(prediction.deviation_pct) if (prediction and prediction.deviation_pct is not None) else 0.0

    hour = reading.timestamp.hour
    day_type = reading.day_type
    is_weekend = (day_type == "weekend")
    is_holiday = (day_type == "holiday")
    is_off_hours = is_weekend or is_holiday or (hour < 8 or hour >= 18)
    
    outdoor_temp = reading.outdoor_temp_c
    occupancy = reading.occupancy_count
    max_cap = building.max_capacity or 500
    occ_ratio = (occupancy / max_cap) if occupancy is not None else None

    # Collect structured evidence facts
    evidence = {
        "actual_energy_kwh": actual_kwh,
        "predicted_energy_kwh": pred_kwh,
        "residual_kwh": residual,
        "deviation_pct": dev_pct,
        "hour_of_day": hour,
        "day_type": day_type,
        "is_off_hours": is_off_hours,
        "operating_status": reading.operating_status,
        "outdoor_temp_c": outdoor_temp,
        "occupancy_count": occupancy,
        "occupancy_ratio": round(occ_ratio, 3) if occ_ratio is not None else None,
        "has_hvac": building.has_hvac,
        "detection_method": anomaly.detection_method,
        "anomaly_score": anomaly.anomaly_score,
    }

    # RULE 1: Severe Negative Drop during Operational Hours (Plausible Meter Failure / Breaker Trip)
    if dev_pct <= -70.0 and (not is_off_hours or reading.operating_status == "normal"):
        return {
            "primary_hypothesis": (
                f"Abnormally low energy consumption ({actual_kwh} kWh vs expected {pred_kwh} kWh, {dev_pct:+.1f}%) "
                f"during operational hours. Plausible sub-station main breaker trip or smart meter telemetry failure."
            ),
            "evidence": evidence,
            "confidence": "high",
            "data_to_confirm": "Check physical breaker switch status at main LT distribution board and verify meter voltage inputs.",
            "recommended_next_action": "Dispatch electrical maintenance team immediately to inspect main breaker and meter connection.",
        }

    # RULE 2: Off-Hours / Low Occupancy Heavy Consumption Spike
    if residual > 0 and is_off_hours and (occ_ratio is not None and occ_ratio <= 0.15):
        confidence = "high" if building.has_hvac else "medium"
        return {
            "primary_hypothesis": (
                f"High electricity usage ({actual_kwh} kWh vs expected {pred_kwh} kWh, {dev_pct:+.1f}%) "
                f"detected outside standard operating hours with minimal occupant presence ({occupancy or 0} people, "
                f"{occ_ratio * 100:.1f}% capacity). Plausible air conditioning, server lab cooling, or lighting left powered on."
            ),
            "evidence": evidence,
            "confidence": confidence,
            "data_to_confirm": "Security guard entry logs, sub-panel breaker feeds for labs, and BMS thermostat runtime logs.",
            "recommended_next_action": "Inspect floors and laboratories for active air conditioning and equipment left running overnight.",
        }

    # RULE 3: Extreme Ambient Heat Cooling Surge
    if residual > 0 and outdoor_temp is not None and outdoor_temp >= 35.0:
        return {
            "primary_hypothesis": (
                f"Consumption increase ({actual_kwh} kWh vs expected {pred_kwh} kWh) strongly correlates with extreme "
                f"ambient outdoor temperature ({outdoor_temp}°C). Indicates elevated chiller plant load and thermal gain across the block."
            ),
            "evidence": evidence,
            "confidence": "high" if building.has_hvac else "medium",
            "data_to_confirm": "Chiller chilled-water supply/return temperature differentials and AHU fan speed logs.",
            "recommended_next_action": "Check chiller setpoints, verify condenser water flow, and inspect blinds/shading on sun-facing facades.",
        }

    # RULE 4: Operational Daytime Surge with Standard Occupancy
    if residual > 0 and not is_off_hours and occ_ratio is not None and occ_ratio > 0.20:
        return {
            "primary_hypothesis": (
                f"Above-average electricity consumption ({actual_kwh} kWh vs expected {pred_kwh} kWh, {dev_pct:+.1f}%) "
                f"during active campus hours with normal occupancy ({occupancy} occupants). May indicate concurrent heavy machinery, "
                f"computer lab utilization, or reduced chiller thermodynamic efficiency."
            ),
            "evidence": evidence,
            "confidence": "medium",
            "data_to_confirm": "Sub-meter logs for specialized lab equipment, departmental workshops, and chiller electrical sub-panels.",
            "recommended_next_action": "Verify if special academic laboratory experiments or symposia were scheduled during this period.",
        }

    # RULE 5: Fallback — Insufficient Context
    return {
        "primary_hypothesis": "Insufficient auxiliary context (weather or occupancy records) to determine a likely cause.",
        "evidence": evidence,
        "confidence": "low",
        "data_to_confirm": "Install ambient temperature logging and automated occupancy turnstile logging for this building block.",
        "recommended_next_action": "Conduct manual walk-through audit of the building to observe operating loads.",
    }

