"""Offline benchmark runner.

Scores every generated scenario through BOTH real systems -- SENTINEL via the
existing `engine.score_signals` fusion, the single-sensor baseline via the
existing `baseline.single_sensor_baseline` -- derives a binary DANGEROUS/SAFE
decision for each, and compares both against the construction-derived ground
truth. No scoring logic is re-implemented here; this harness only calls the
real code and tallies the outcomes.

Runs fully offline: pure scoring, no database, no LLM, no network. Safe to run
repeatedly at zero cost.

    python -m app.benchmark.run [--count N] [--seed S] [--out PATH]

SYNTHETIC ONLY -- results are a demonstration on generated scenarios, not
validation against real incidents.
"""

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from app.benchmark.generate import (
    Scenario,
    generate_scenarios,
    generation_parameters,
)
from app.risk.baseline import single_sensor_baseline
from app.risk.engine import CRITICAL_Z, _estimate_time_to_critical, score_signals

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "benchmark_results.json"

SYNTHETIC_DISCLAIMER = (
    "SYNTHETIC RESULTS: measured on randomly generated scenarios from a "
    "documented neutral distribution, NOT validated against real-world "
    "incidents."
)

# Binary decisions from each system's REAL output.
# SENTINEL: the fused risk level is HIGH or CRITICAL.
# Baseline: any single sensor crosses its own trip point (alarm == True).
SENTINEL_DANGEROUS_LEVELS = {"HIGH", "CRITICAL"}


def _score_sentinel(scenario: Scenario) -> tuple[str, float | None]:
    """One real SENTINEL scoring pass -> (decision, lead_time).

    The decision is the fused risk level. The lead time reuses the engine's
    existing projection (`_estimate_time_to_critical`) -- SAME formula, no new
    prediction logic -- but SCOPED to the elevated sensors actually driving
    the compound hazard. Excluding calm sensors is a measurement-scoping fix:
    a calm sensor drifting on measurement noise is not a warning, and letting
    it drive the projection produced spurious minutes-long "lead times". The
    engine's own live projection is unchanged by this benchmark-only scoping."""
    result = score_signals(scenario.per_sensor, scenario.by_type)
    decision = "DANGEROUS" if result["risk_level"] in SENTINEL_DANGEROUS_LEVELS else "SAFE"
    elevated_sensors = [
        s for s in scenario.per_sensor if s["sensor_type"] in scenario.elevated_types
    ]
    lead_time = _estimate_time_to_critical(elevated_sensors)
    return decision, lead_time


def _baseline_decision(scenario: Scenario) -> str:
    result = single_sensor_baseline(scenario.per_sensor, CRITICAL_Z)
    return "DANGEROUS" if result["alarm"] else "SAFE"


def _lead_time_stats(scenarios: list[Scenario]) -> dict:
    """Warning lead time = seconds before a sensor reaches its critical
    threshold, at the moment SENTINEL flags a rising compound hazard.

    A scenario contributes only when: it is a genuine compound hazard
    (ground truth DANGEROUS), SENTINEL actually flags it (so a warning is
    really being given), AND the engine's time_to_critical projection is
    valid (a sensor is rising toward critical and still below it -- i.e. the
    warning genuinely precedes the critical threshold). Compound hazards
    already past critical, or that SENTINEL misses, contribute no lead time."""
    lead_times = sorted(
        s.sentinel_time_to_critical
        for s in scenarios
        if s.ground_truth == "DANGEROUS"
        and s.sentinel_decision == "DANGEROUS"
        and s.sentinel_time_to_critical is not None
    )
    n = len(lead_times)
    if n == 0:
        return {"sample_size": 0, "note": "no rising compound hazards with a valid projection"}

    def pct(p: float) -> float:
        return round(lead_times[min(n - 1, int(p * n))], 1)

    return {
        "description": (
            "Seconds of warning before an ELEVATED sensor reaches its critical "
            "threshold, when SENTINEL flags a rising compound hazard (engine "
            "time_to_critical projection, scoped to the hazard-driving sensors). "
            "Synthetic scenarios."
        ),
        "sample_size": n,
        "mean_seconds": round(statistics.fmean(lead_times), 1),
        "median_seconds": round(statistics.median(lead_times), 1),
        "min_seconds": round(lead_times[0], 1),
        "max_seconds": round(lead_times[-1], 1),
        "p25_seconds": pct(0.25),
        "p75_seconds": pct(0.75),
    }


def confusion_matrix(scenarios: list[Scenario], decision_attr: str) -> dict:
    """Confusion of a system's decisions against ground truth. DANGEROUS is
    the positive class, so a false NEGATIVE is a dangerous scenario the system
    called safe -- the life-critical error."""
    tp = fp = tn = fn = 0
    for s in scenarios:
        decided = getattr(s, decision_attr)
        gt_danger = s.ground_truth == "DANGEROUS"
        dec_danger = decided == "DANGEROUS"
        if gt_danger and dec_danger:
            tp += 1
        elif gt_danger and not dec_danger:
            fn += 1
        elif not gt_danger and dec_danger:
            fp += 1
        else:
            tn += 1
    dangerous_total = tp + fn
    fnr = fn / dangerous_total if dangerous_total else 0.0
    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "false_negative_rate": round(fnr, 4),
    }


def run_benchmark(count: int = 200, seed: int = 42,
                  class_weights: tuple = (1, 1, 1)) -> dict:
    """Generate, score through both real systems, and assemble the results
    dict (also the shape written to JSON)."""
    scenarios = generate_scenarios(count, seed=seed, class_weights=class_weights)
    for s in scenarios:
        s.sentinel_decision, s.sentinel_time_to_critical = _score_sentinel(s)
        s.baseline_decision = _baseline_decision(s)

    sentinel = confusion_matrix(scenarios, "sentinel_decision")
    baseline = confusion_matrix(scenarios, "baseline_decision")

    # Headline: compound (DANGEROUS) scenarios the baseline missed but SENTINEL
    # caught -- the individually-moderate hazards a single-sensor alarm ignores.
    compound = [s for s in scenarios if s.ground_truth == "DANGEROUS"]
    baseline_missed_sentinel_caught = sum(
        1 for s in compound
        if s.baseline_decision == "SAFE" and s.sentinel_decision == "DANGEROUS"
    )
    # Honesty: also count dangerous scenarios BOTH miss, so the report can't
    # imply SENTINEL is flawless.
    both_missed = sum(
        1 for s in compound
        if s.baseline_decision == "SAFE" and s.sentinel_decision == "SAFE"
    )

    fnr_base = baseline["false_negative_rate"]
    fnr_sent = sentinel["false_negative_rate"]
    abs_reduction = round(fnr_base - fnr_sent, 4)
    rel_reduction = round((fnr_base - fnr_sent) / fnr_base, 4) if fnr_base else 0.0

    lead_time = _lead_time_stats(scenarios)

    class_breakdown: dict[str, int] = {}
    for s in scenarios:
        class_breakdown[s.scenario_class] = class_breakdown.get(s.scenario_class, 0) + 1

    return {
        "synthetic": True,
        "disclaimer": SYNTHETIC_DISCLAIMER,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario_count": count,
        "seed": seed,
        "generation": generation_parameters(),
        "class_breakdown": class_breakdown,
        "ground_truth_breakdown": {
            "SAFE": sum(1 for s in scenarios if s.ground_truth == "SAFE"),
            "DANGEROUS": len(compound),
        },
        "systems": {
            "sentinel": {"decision_rule": "risk_level in {HIGH, CRITICAL}",
                         "confusion": sentinel},
            "single_sensor_baseline": {
                "decision_rule": f"any sensor z >= {CRITICAL_Z} (alarm)",
                "confusion": baseline},
        },
        "false_negative_rate_reduction": {
            "baseline_fnr": fnr_base,
            "sentinel_fnr": fnr_sent,
            "absolute_reduction": abs_reduction,
            "relative_reduction": rel_reduction,
        },
        "prediction_lead_time": lead_time,
        "compound_dangerous_total": len(compound),
        "compound_missed_by_baseline_caught_by_sentinel": baseline_missed_sentinel_caught,
        "compound_missed_by_both": both_missed,
    }


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def print_summary(results: dict) -> None:
    """Clean console summary table."""
    s = results["systems"]["sentinel"]["confusion"]
    b = results["systems"]["single_sensor_baseline"]["confusion"]
    red = results["false_negative_rate_reduction"]
    cb = results["class_breakdown"]

    print("=" * 66)
    print(" SENTINEL vs SINGLE-SENSOR BASELINE  --  OFFLINE DETECTION BENCHMARK")
    print("=" * 66)
    print(f" {results['disclaimer']}")
    print("-" * 66)
    print(f" Scenarios: {results['scenario_count']}  (seed {results['seed']})   "
          f"normal={cb.get('normal', 0)}  single_spike={cb.get('single_spike', 0)}  "
          f"compound={cb.get('compound', 0)}")
    gt = results["ground_truth_breakdown"]
    print(f" Ground truth (by construction): SAFE={gt['SAFE']}  DANGEROUS={gt['DANGEROUS']}")
    print("-" * 66)
    header = f" {'metric':<26}{'baseline':>16}{'SENTINEL':>16}"
    print(header)
    print("-" * 66)
    rows = [
        ("true positives",  b["true_positives"],  s["true_positives"]),
        ("false positives", b["false_positives"], s["false_positives"]),
        ("true negatives",  b["true_negatives"],  s["true_negatives"]),
        ("FALSE NEGATIVES",  b["false_negatives"], s["false_negatives"]),
    ]
    for name, bv, sv in rows:
        print(f" {name:<26}{bv:>16}{sv:>16}")
    print(f" {'false-negative rate':<26}"
          f"{_pct(b['false_negative_rate']):>16}{_pct(s['false_negative_rate']):>16}")
    print("-" * 66)
    print(f" False-negative-rate reduction (baseline -> SENTINEL):")
    print(f"     absolute: {_pct(red['absolute_reduction'])} points     "
          f"relative: {_pct(red['relative_reduction'])}")
    print(f" Compound hazards the baseline MISSED but SENTINEL CAUGHT: "
          f"{results['compound_missed_by_baseline_caught_by_sentinel']}"
          f" of {results['compound_dangerous_total']}")
    if results["compound_missed_by_both"]:
        print(f" (honest caveat) compound hazards BOTH missed: "
              f"{results['compound_missed_by_both']}")
    print("-" * 66)
    lt = results["prediction_lead_time"]
    if lt["sample_size"]:
        print(f" Prediction lead time (rising compound hazards, n={lt['sample_size']}):")
        print(f"     mean {lt['mean_seconds']}s   median {lt['median_seconds']}s   "
              f"range {lt['min_seconds']}-{lt['max_seconds']}s")
    else:
        print(f" Prediction lead time: {lt['note']}")
    print("=" * 66)


def main() -> None:
    parser = argparse.ArgumentParser(description="SENTINEL offline detection benchmark")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    results = run_benchmark(count=args.count, seed=args.seed)
    print_summary(results)
    args.out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
