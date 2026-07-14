"""Interpretable, hand-authored rule layer.

Every point awarded here traces back to a specific sensor reading, so the
result can be explained to a human end to end -- this is the layer that
keeps the risk engine from being a pure black box (see ML layer in
train_model.py / engine.py for the complementary pattern-detection half).

Weights below are illustrative, chosen by relative real-world severity
(gas leak > pressure rupture > temperature drift). A production system
would source these from OISD/DGMS regulatory thresholds instead -- that's
exactly the job of the Compliance Agent planned for a later milestone.
"""

from app.risk.features import ELEVATED_Z_THRESHOLD

SENSOR_TYPE_WEIGHT = {"gas": 35, "temperature": 20, "pressure": 30}

# How many additional z-scores past the elevated threshold it takes to go
# from "just barely elevated" (severity_factor 0) to "maximally severe"
# (severity_factor 1) for that sensor's contribution.
SEVERITY_RANGE = 3.0


def _severity_factor(z: float) -> float:
    if z <= ELEVATED_Z_THRESHOLD:
        return 0.0
    return min(1.0, (z - ELEVATED_Z_THRESHOLD) / SEVERITY_RANGE)


def score_zone(per_sensor: list[dict], by_type: dict) -> dict:
    """Returns {"rule_score": float, "contributing_signals": [...]}."""
    contributing_signals = []
    base_score = 0.0

    for sensor in per_sensor:
        severity = _severity_factor(sensor["z"])
        if severity <= 0:
            continue
        weight = SENSOR_TYPE_WEIGHT[sensor["sensor_type"]]
        contribution = weight * severity
        base_score += contribution

        trend = " and rising fast" if sensor["rate_z"] > 1.0 else ""
        contributing_signals.append({
            "source": "rule",
            "sensor_id": sensor["sensor_id"],
            "sensor_type": sensor["sensor_type"],
            "description": (
                f"{sensor['sensor_type']} sensor {sensor['sensor_id']} reading "
                f"{sensor['latest_value']} {sensor['unit']} is {sensor['z']:.1f}"
                f"σ above its normal baseline{trend}"
            ),
            "weight_contribution": round(contribution, 1),
        })

    elevated_types = [t for t, s in by_type.items() if s["z"] > ELEVATED_Z_THRESHOLD]
    n_present_types = len(by_type)
    n_elevated_types = len(elevated_types)

    multiplier = 1.0
    if n_elevated_types >= 2:
        multiplier = 1.5
    if n_present_types >= 2 and n_elevated_types == n_present_types:
        multiplier = 2.0

    if multiplier > 1.0:
        contributing_signals.append({
            "source": "rule",
            "sensor_id": None,
            "sensor_type": None,
            "description": (
                f"Compound risk: {n_elevated_types} different sensor types "
                f"({', '.join(elevated_types)}) elevated simultaneously in this "
                f"zone -- individually none may cross an alert threshold, but "
                f"together they compound"
            ),
            "weight_contribution": f"{multiplier}x multiplier",
        })

    rule_score = max(0.0, min(100.0, base_score * multiplier))
    return {"rule_score": rule_score, "contributing_signals": contributing_signals}
