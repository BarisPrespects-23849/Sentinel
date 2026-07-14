"""Shared feature engineering for the risk engine.

CRITICAL: this module is imported by BOTH the training script
(train_model.py) and the live scoring path (signals.py -> engine.py).
That's deliberate, not incidental -- if training and inference ever
compute features differently, the model's learned weights stop meaning
what they were trained to mean. This is called "train/serve skew" and is
one of the most common ways real ML systems silently break.
"""

SENSOR_TYPES = ["gas", "temperature", "pressure"]

# A sensor type counts as "elevated" once its live value is this many
# standard deviations above its normal baseline (see TYPE_DEFAULTS in
# app.simulator.sensors -- we treat that same baseline/noise_stddev as
# the "known normal operating range" here too).
ELEVATED_Z_THRESHOLD = 2.0

FEATURE_NAMES = [
    "gas_z", "gas_rate_z",
    "temperature_z", "temperature_rate_z",
    "pressure_z", "pressure_rate_z",
    "n_present", "n_elevated",
]


def build_feature_vector(signals: dict) -> list[float]:
    """signals: {sensor_type: {"z": float, "rate_z": float}} for whichever
    sensor types are physically present in a zone. Missing types default
    to z=0/rate_z=0 ("at baseline"), so the same fixed-length feature
    vector works for zones with different sensor mixes.
    """
    n_present = len(signals)
    n_elevated = sum(1 for s in signals.values() if s["z"] > ELEVATED_Z_THRESHOLD)

    vector = []
    for sensor_type in SENSOR_TYPES:
        s = signals.get(sensor_type, {"z": 0.0, "rate_z": 0.0})
        vector.append(s["z"])
        vector.append(s["rate_z"])
    vector.append(float(n_present))
    vector.append(float(n_elevated))
    return vector
