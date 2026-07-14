"""Tests for the hybrid engine -- including THE rubric property: compound
anomalies must dramatically outscore single-sensor anomalies, in both the
rules layer and the ML layer, whether the hazard is rising or plateaued."""

from app.risk.engine import (
    _estimate_time_to_critical,
    risk_level,
    score_signals,
)


def _sensor(sensor_type, z, rate_z):
    return {"sensor_id": f"s-{sensor_type}", "sensor_type": sensor_type,
            "z": z, "rate_z": rate_z}


def _signals(spec):
    """spec: {sensor_type: (z, rate_z)} -> (per_sensor, by_type)"""
    per_sensor = [
        {
            "sensor_id": f"test-{t}",
            "sensor_type": t,
            "unit": "u",
            "latest_value": 0.0,
            "z": z,
            "rate_z": rate_z,
        }
        for t, (z, rate_z) in spec.items()
    ]
    by_type = {t: {"z": z, "rate_z": rate_z} for t, (z, rate_z) in spec.items()}
    return per_sensor, by_type


def test_single_sensor_stays_low_ml_agrees():
    result = score_signals(*_signals({"gas": (10.0, 1.0), "temperature": (0.0, 0.0)}))
    assert result["risk_level"] in ("LOW", "MEDIUM")
    assert result["ml_score"] < 20


def test_compound_rising_fires_both_layers():
    result = score_signals(
        *_signals({"gas": (10.0, 1.5), "temperature": (8.0, 1.0)})
    )
    assert result["ml_score"] > 80
    assert result["risk_score"] > 60


def test_compound_plateaued_fires_ml_too():
    # Regression test for the steady-state blind spot: a hazard that has
    # STOPPED rising (rate_z = 0, e.g. what-if sliders or a stabilized
    # leak) must still be recognized as compound by the ML layer.
    result = score_signals(
        *_signals({"gas": (10.0, 0.0), "temperature": (8.0, 0.0)})
    )
    assert result["ml_score"] > 80


def test_compound_beats_single_dramatically():
    single = score_signals(*_signals({"gas": (12.0, 0.0)}))["risk_score"]
    compound = score_signals(
        *_signals({"gas": (12.0, 0.0), "temperature": (10.0, 0.0)})
    )["risk_score"]
    assert compound > single * 2


def test_risk_level_boundaries():
    assert risk_level(0) == "LOW"
    assert risk_level(29.9) == "LOW"
    assert risk_level(30) == "MEDIUM"
    assert risk_level(60) == "HIGH"
    assert risk_level(85) == "CRITICAL"
    assert risk_level(100) == "CRITICAL"


def test_calm_noise_drift_does_not_produce_a_countdown():
    # A calm sensor (below the elevation threshold) drifting up on measurement
    # noise must NOT drive a time-to-critical projection -- it is not a warning.
    calm_drift = [_sensor("temperature", z=0.5, rate_z=0.05)]
    assert _estimate_time_to_critical(calm_drift) is None


def test_elevated_rising_sensor_does_produce_a_countdown():
    # A genuinely-elevated sensor rising toward critical is a real warning.
    elevated_rising = [_sensor("gas", z=3.0, rate_z=0.05)]
    ttc = _estimate_time_to_critical(elevated_rising)
    assert ttc is not None and ttc > 0


def test_elevated_sensor_drives_countdown_not_the_calm_one():
    # With both present, the elevated rising sensor drives the countdown and
    # the calm noise-drift sensor is ignored (no spurious longer projection).
    per_sensor = [
        _sensor("gas", z=3.0, rate_z=0.05),          # -> (6-3)/0.05 = 60s
        _sensor("temperature", z=0.4, rate_z=0.03),  # calm drift, must be ignored
    ]
    assert _estimate_time_to_critical(per_sensor) == 60.0
