"""Unit tests for the interpretable rules layer."""

from app.risk import rules


def _sensor(sensor_type, z, rate_z=0.0, sensor_id=None):
    return {
        "sensor_id": sensor_id or f"test-{sensor_type}",
        "sensor_type": sensor_type,
        "unit": "u",
        "latest_value": 0.0,
        "z": z,
        "rate_z": rate_z,
    }


def test_calm_zone_scores_zero():
    per_sensor = [_sensor("gas", 0.5), _sensor("temperature", -1.0)]
    by_type = {"gas": {"z": 0.5, "rate_z": 0}, "temperature": {"z": -1.0, "rate_z": 0}}
    result = rules.score_zone(per_sensor, by_type)
    assert result["rule_score"] == 0.0
    assert result["contributing_signals"] == []


def test_below_threshold_contributes_nothing():
    # Exactly at the elevated threshold is NOT elevated (strictly greater).
    per_sensor = [_sensor("gas", 2.0)]
    by_type = {"gas": {"z": 2.0, "rate_z": 0}}
    assert rules.score_zone(per_sensor, by_type)["rule_score"] == 0.0


def test_single_sensor_capped_at_type_weight():
    # One wildly elevated gas sensor can never exceed the gas weight alone.
    per_sensor = [_sensor("gas", 50.0)]
    by_type = {"gas": {"z": 50.0, "rate_z": 0}}
    result = rules.score_zone(per_sensor, by_type)
    assert result["rule_score"] == rules.SENSOR_TYPE_WEIGHT["gas"]


def test_compound_multiplier_applies():
    # Two elevated types must score MORE than the sum of each alone --
    # this is the core "compound > sum of parts" property.
    gas_alone = rules.score_zone(
        [_sensor("gas", 10.0)], {"gas": {"z": 10.0, "rate_z": 0}}
    )["rule_score"]
    temp_alone = rules.score_zone(
        [_sensor("temperature", 10.0)], {"temperature": {"z": 10.0, "rate_z": 0}}
    )["rule_score"]
    both = rules.score_zone(
        [_sensor("gas", 10.0), _sensor("temperature", 10.0)],
        {"gas": {"z": 10.0, "rate_z": 0}, "temperature": {"z": 10.0, "rate_z": 0}},
    )["rule_score"]
    assert both > gas_alone + temp_alone

    compound_notes = [
        s
        for s in rules.score_zone(
            [_sensor("gas", 10.0), _sensor("temperature", 10.0)],
            {"gas": {"z": 10.0, "rate_z": 0}, "temperature": {"z": 10.0, "rate_z": 0}},
        )["contributing_signals"]
        if s["description"].startswith("Compound risk")
    ]
    assert len(compound_notes) == 1


def test_score_never_exceeds_100():
    per_sensor = [
        _sensor("gas", 100.0),
        _sensor("temperature", 100.0),
        _sensor("pressure", 100.0),
    ]
    by_type = {t: {"z": 100.0, "rate_z": 0} for t in ("gas", "temperature", "pressure")}
    assert rules.score_zone(per_sensor, by_type)["rule_score"] == 100.0


def test_two_sensors_of_same_type_both_contribute():
    # Two independent gas sensors agreeing is stronger evidence than one.
    one = rules.score_zone(
        [_sensor("gas", 10.0, sensor_id="gas-a")],
        {"gas": {"z": 10.0, "rate_z": 0}},
    )["rule_score"]
    two = rules.score_zone(
        [_sensor("gas", 10.0, sensor_id="gas-a"), _sensor("gas", 10.0, sensor_id="gas-b")],
        {"gas": {"z": 10.0, "rate_z": 0}},
    )["rule_score"]
    assert two > one


def test_rising_sensor_flagged_in_description():
    result = rules.score_zone(
        [_sensor("gas", 10.0, rate_z=2.0)], {"gas": {"z": 10.0, "rate_z": 2.0}}
    )
    assert "rising fast" in result["contributing_signals"][0]["description"]
