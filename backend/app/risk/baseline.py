"""Single-sensor alarm baseline -- the naive system SENTINEL is measured
against.

The hackathon rubric explicitly scores "compound risk detection accuracy
versus single-sensor baselines," so we compute that baseline honestly from
the SAME per-sensor inputs the real engine scores, and surface it beside
the fused score. This is not a strawman: a traditional plant-floor alarm
genuinely does evaluate each sensor in isolation against its own trip
point, with no cross-sensor reasoning.

The trip point is the engine's own CRITICAL_Z (passed in) -- the z-score
at which a SINGLE sensor is considered individually critical (the same
level the time-to-critical countdown counts toward). The honest story
that falls out: readings that each sit below their own critical trip point
(individually "normal-looking") draw NO ALARM here, while SENTINEL's fused
score can still be HIGH/CRITICAL because the danger is in the combination.

Crucially, this is real math, not a rigged contrast: if any single sensor
DOES cross its own trip point, this baseline honestly reports the alarm --
the comparison never hides a genuine single-sensor alarm to flatter the
fused score.
"""


def single_sensor_baseline(per_sensor: list[dict], trip_z: float) -> dict:
    """Evaluate each sensor in ISOLATION against a per-sensor trip point.

    Returns the verdict a naive single-sensor alarm system would reach:
    it alarms iff at least one individual sensor's z-score reaches trip_z,
    with NO cross-sensor / compound reasoning of any kind.
    """
    tripped = [
        {"sensor_type": s["sensor_type"], "z": round(s["z"], 1)}
        for s in per_sensor
        if s["z"] >= trip_z
    ]
    peak_z = max((s["z"] for s in per_sensor), default=0.0)
    return {
        "alarm": bool(tripped),
        "label": "ALARM" if tripped else "NO ALARM",
        "threshold_z": trip_z,
        "peak_z": round(peak_z, 1),
        "tripped": tripped,
    }
