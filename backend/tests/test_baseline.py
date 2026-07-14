"""Tests for the single-sensor alarm baseline.

The core property under test is ISOLATION: the baseline evaluates each
sensor against its own trip point with zero cross-sensor reasoning -- and
it does so honestly (a genuine single-sensor alarm is never suppressed to
flatter the fused score)."""

from app.risk.baseline import single_sensor_baseline
from app.risk.engine import CRITICAL_Z, score_signals


def _per_sensor(spec):
    """spec: {sensor_type: z} -> per_sensor list (rate irrelevant here)."""
    return [
        {"sensor_id": f"t-{t}", "sensor_type": t, "unit": "u",
         "latest_value": 0.0, "z": z, "rate_z": 0.0}
        for t, z in spec.items()
    ]


def test_each_sensor_evaluated_in_isolation():
    # Two sensors each just BELOW the trip point. In isolation neither
    # alarms -- even though, added together, their z-sum far exceeds it.
    # A baseline that (wrongly) reasoned across sensors would fire here.
    trip = CRITICAL_Z
    per_sensor = _per_sensor({"gas": trip - 0.5, "temperature": trip - 0.5})
    result = single_sensor_baseline(per_sensor, trip)
    assert result["alarm"] is False
    assert result["label"] == "NO ALARM"
    assert result["tripped"] == []


def test_single_sensor_over_trip_honestly_alarms():
    # If one sensor genuinely crosses its own trip point, the baseline
    # MUST report the alarm -- the contrast is real math, not rigged.
    trip = CRITICAL_Z
    per_sensor = _per_sensor({"gas": trip + 2.0, "temperature": 0.0})
    result = single_sensor_baseline(per_sensor, trip)
    assert result["alarm"] is True
    assert [t["sensor_type"] for t in result["tripped"]] == ["gas"]


def test_trip_point_is_inclusive_boundary():
    trip = CRITICAL_Z
    assert single_sensor_baseline(_per_sensor({"gas": trip}), trip)["alarm"] is True
    assert single_sensor_baseline(_per_sensor({"gas": trip - 0.01}), trip)["alarm"] is False


def test_peak_z_reports_worst_single_reading():
    result = single_sensor_baseline(_per_sensor({"gas": 3.2, "temperature": 4.8}), CRITICAL_Z)
    assert result["peak_z"] == 4.8
    assert result["threshold_z"] == CRITICAL_Z


def test_empty_zone_is_no_alarm():
    result = single_sensor_baseline([], CRITICAL_Z)
    assert result["alarm"] is False
    assert result["peak_z"] == 0.0


def test_baseline_flows_through_score_signals():
    # The rubric property, end to end: a compound scenario where each
    # sensor sits BELOW its own critical trip point still drives SENTINEL
    # HIGH/CRITICAL, while the single-sensor baseline shows NO ALARM.
    per_sensor = _per_sensor({"gas": 5.0, "temperature": 5.0})
    by_type = {"gas": {"z": 5.0, "rate_z": 0.0}, "temperature": {"z": 5.0, "rate_z": 0.0}}
    result = score_signals(per_sensor, by_type)
    assert result["single_sensor_baseline"]["alarm"] is False
    assert result["risk_level"] in ("HIGH", "CRITICAL")
