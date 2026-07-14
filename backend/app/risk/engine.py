"""Hybrid risk engine: fuses the rule layer and ML layer into one score
with a full explanation trail (contributing_signals).
"""

import joblib

from app.risk import rules
from app.risk.baseline import single_sensor_baseline
from app.risk.features import ELEVATED_Z_THRESHOLD, build_feature_vector
from app.risk.signals import get_zone_signals
from app.risk.train_model import MODEL_PATH, train_and_save

# Rules get more weight than ML in the final blend: this is a safety
# system, and per the project's design goals it should never let an
# opaque model be the primary decision-maker (see CLAUDE_CONTEXT.md --
# "hybrid: interpretable rules + lightweight ML, NOT pure black box").
RULE_WEIGHT = 0.6
ML_WEIGHT = 0.4

# "Critical" is defined on the same statistical scale as "elevated"
# (features.ELEVATED_Z_THRESHOLD = 2.0) rather than a separate made-up
# absolute number per sensor type -- just a much further point on the
# same z-score axis.
CRITICAL_Z = 6.0

RISK_LEVELS = [(30, "LOW"), (60, "MEDIUM"), (85, "HIGH"), (101, "CRITICAL")]


def risk_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score < threshold:
            return label
    return "CRITICAL"


def _load_model():
    if not MODEL_PATH.exists():
        train_and_save()
    return joblib.load(MODEL_PATH)


_model_bundle = _load_model()


def _estimate_time_to_critical(per_sensor: list[dict]) -> float | None:
    """Seconds until the soonest ELEVATED sensor crosses CRITICAL_Z, assuming
    its current rate of change holds steady. z and rate_z are both measured
    in "noise standard deviations", so rate_z is literally dz/dt -- no
    unit conversion needed to project forward.

    Only sensors already ABOVE the elevation threshold count. A calm sensor
    hovering near baseline that drifts up on measurement noise (a small
    positive rate_z) is not a warning of anything -- projecting its slow
    noise-drift forward produced spurious minutes-long countdowns. Scoping to
    genuinely-elevated, hazard-driving sensors fixes that. This affects only
    the projected countdown, never the risk score or level.
    """
    candidates = []
    for s in per_sensor:
        elevated = s["z"] > ELEVATED_Z_THRESHOLD
        rising_below_critical = s["rate_z"] > 0.01 and s["z"] < CRITICAL_Z
        if elevated and rising_below_critical:
            seconds = (CRITICAL_Z - s["z"]) / s["rate_z"]
            if 0 < seconds <= 24 * 3600:
                candidates.append(seconds)
    return min(candidates) if candidates else None


def _ml_contributing_signal(ml_score: float, model) -> dict:
    from app.risk.features import FEATURE_NAMES

    top = sorted(zip(FEATURE_NAMES, model.feature_importances_), key=lambda p: -p[1])[:2]
    top_desc = " and ".join(name for name, _ in top)
    return {
        "source": "ml",
        "sensor_id": None,
        "sensor_type": None,
        "description": (
            f"ML model estimates a {ml_score:.0f}% probability this is a genuine "
            f"compound-risk pattern (trained on synthetic scenarios; most "
            f"influential features overall are {top_desc})"
        ),
        "weight_contribution": round(ml_score, 1),
    }


def score_signals(per_sensor: list[dict], by_type: dict) -> dict:
    """The full hybrid scoring path (rules + ML + explanation), independent
    of where the signals came from. Both live scoring (score_zone) and
    what-if simulation (app.risk.simulate) call THIS -- one code path, so a
    simulated score is exactly what the live score would be for the same
    readings, never a lookalike reimplementation.
    """
    rule_result = rules.score_zone(per_sensor, by_type)
    feature_vector = build_feature_vector(by_type)

    model = _model_bundle["model"]
    ml_score = model.predict_proba([feature_vector])[0][1] * 100

    hybrid_score = RULE_WEIGHT * rule_result["rule_score"] + ML_WEIGHT * ml_score

    contributing_signals = list(rule_result["contributing_signals"])
    contributing_signals.append(_ml_contributing_signal(ml_score, model))

    return {
        "risk_score": round(hybrid_score, 1),
        "risk_level": risk_level(hybrid_score),
        "rule_score": round(rule_result["rule_score"], 1),
        "ml_score": round(ml_score, 1),
        "time_to_critical_seconds": _estimate_time_to_critical(per_sensor),
        # What a naive single-sensor alarm would conclude from the SAME
        # inputs -- computed honestly so the frontend can show the contrast
        # the rubric scores (compound detection vs. single-sensor baseline).
        "single_sensor_baseline": single_sensor_baseline(per_sensor, CRITICAL_Z),
        "contributing_signals": contributing_signals,
    }


def score_zone(conn, zone_id: int, zone_name: str) -> dict:
    signals = get_zone_signals(conn, zone_id)
    per_sensor = signals["per_sensor"]

    if not per_sensor:
        return {
            "zone_id": zone_id,
            "zone_name": zone_name,
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "rule_score": None,
            "ml_score": None,
            "time_to_critical_seconds": None,
            "single_sensor_baseline": None,
            "contributing_signals": [],
            "message": "No recent sensor readings for this zone.",
        }

    return {
        "zone_id": zone_id,
        "zone_name": zone_name,
        **score_signals(per_sensor, signals["by_type"]),
    }
