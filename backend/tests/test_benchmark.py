"""Tests for the offline detection benchmark.

These assert the harness is FAIR and WELL-FORMED -- the requested count and
class balance, ground truth derived from construction (not from either
scorer), and a valid end-to-end confusion matrix. They deliberately do NOT
assert a specific false-negative number: pinning the metric would make the
test brittle and tempt tuning the scenario data to hit the test, which is
exactly the dishonesty the benchmark is meant to avoid.
"""

from app.benchmark.generate import (
    CALM_Z_RANGE,
    ELEVATED_Z_RANGE,
    generate_scenarios,
)
from app.benchmark.run import confusion_matrix, run_benchmark
from app.risk.features import ELEVATED_Z_THRESHOLD, SENSOR_TYPES


def test_generator_produces_requested_count():
    assert len(generate_scenarios(200)) == 200
    assert len(generate_scenarios(50)) == 50


def test_class_balance_is_neutral_by_default():
    scenarios = generate_scenarios(210)  # divisible by 3
    counts = {c: 0 for c in ("normal", "single_spike", "compound")}
    for s in scenarios:
        counts[s.scenario_class] += 1
    assert sum(counts.values()) == 210
    # Equal 1:1:1 mix (exact here since 210 is divisible by 3).
    assert counts["normal"] == counts["single_spike"] == counts["compound"] == 70


def test_ground_truth_comes_from_construction_not_a_scorer():
    # The label must be a pure function of how many types were elevated,
    # never a scorer's opinion.
    for s in generate_scenarios(200):
        expected = "DANGEROUS" if len(s.elevated_types) >= 2 else "SAFE"
        assert s.ground_truth == expected
        # And it matches the class definition.
        if s.scenario_class == "compound":
            assert s.ground_truth == "DANGEROUS"
            assert len(s.elevated_types) >= 2
        else:  # normal / single_spike
            assert s.ground_truth == "SAFE"
            assert len(s.elevated_types) <= 1


def test_elevated_and_calm_z_ranges_are_unambiguous():
    # Elevated sensors sit above the elevation threshold, calm ones below,
    # so the elevated-type count is never ambiguous.
    for s in generate_scenarios(200):
        for sensor in s.per_sensor:
            if sensor["sensor_type"] in s.elevated_types:
                assert sensor["z"] >= ELEVATED_Z_RANGE[0] > ELEVATED_Z_THRESHOLD
            else:
                assert sensor["z"] <= CALM_Z_RANGE[1] < ELEVATED_Z_THRESHOLD


def test_generation_is_deterministic_for_a_seed():
    a = generate_scenarios(100, seed=7)
    b = generate_scenarios(100, seed=7)
    assert [x.ground_truth for x in a] == [y.ground_truth for y in b]
    assert a[0].per_sensor[0]["z"] == b[0].per_sensor[0]["z"]


def test_all_three_sensor_types_present_each_scenario():
    for s in generate_scenarios(60):
        assert {x["sensor_type"] for x in s.per_sensor} == set(SENSOR_TYPES)
        assert set(s.by_type) == set(SENSOR_TYPES)


def test_harness_runs_end_to_end_and_matrix_is_valid():
    results = run_benchmark(count=120, seed=1)
    for system in ("sentinel", "single_sensor_baseline"):
        cm = results["systems"][system]["confusion"]
        total = (cm["true_positives"] + cm["false_positives"]
                 + cm["true_negatives"] + cm["false_negatives"])
        # Every scenario is counted exactly once.
        assert total == 120
        # Positives (TP+FN) must equal the ground-truth dangerous count.
        assert cm["true_positives"] + cm["false_negatives"] == \
            results["ground_truth_breakdown"]["DANGEROUS"]
        assert 0.0 <= cm["false_negative_rate"] <= 1.0
    assert results["synthetic"] is True


def test_confusion_matrix_counts_false_negatives_correctly():
    # A hand-built case: one DANGEROUS scenario the system calls SAFE must
    # register as exactly one false negative.
    scenarios = generate_scenarios(10, seed=3)
    danger = next(s for s in scenarios if s.ground_truth == "DANGEROUS")
    safe = next(s for s in scenarios if s.ground_truth == "SAFE")
    danger.sentinel_decision = "SAFE"   # missed danger -> false negative
    safe.sentinel_decision = "SAFE"     # correct -> true negative
    cm = confusion_matrix([danger, safe], "sentinel_decision")
    assert cm["false_negatives"] == 1
    assert cm["true_negatives"] == 1
    assert cm["true_positives"] == 0
    assert cm["false_positives"] == 0


def test_lead_time_field_is_computed_and_non_negative():
    results = run_benchmark(count=200, seed=42)
    lt = results["prediction_lead_time"]
    assert "sample_size" in lt
    # This distribution produces rising compound hazards, so lead time applies.
    assert lt["sample_size"] > 0
    for key in ("mean_seconds", "median_seconds", "min_seconds", "max_seconds"):
        assert key in lt
        # Warning lead time is time-until-critical: never negative.
        assert lt[key] >= 0
    # Sanity ordering.
    assert lt["min_seconds"] <= lt["median_seconds"] <= lt["max_seconds"]


def test_benchmark_results_endpoint(client):
    # Read-only endpoint serves the written JSON (synthetic-tagged).
    res = client.get("/benchmark/results")
    assert res.status_code == 200
    body = res.json()
    assert body["synthetic"] is True
    assert "prediction_lead_time" in body
    assert body["systems"]["sentinel"]["confusion"]["false_negatives"] >= 0
