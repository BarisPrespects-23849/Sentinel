"""Defines how each simulated sensor's value evolves over time."""

import random
from dataclasses import dataclass

# Typical resting values and noise characteristics per sensor type.
# These are illustrative, not sourced from a real plant.
TYPE_DEFAULTS = {
    "gas": {"baseline": 8.0, "unit": "ppm", "noise_stddev": 0.8, "drift_stddev": 0.15,
            "spike_probability": 0.02, "spike_magnitude": 25.0},
    "temperature": {"baseline": 36.0, "unit": "celsius", "noise_stddev": 0.4, "drift_stddev": 0.08,
                     "spike_probability": 0.015, "spike_magnitude": 8.0},
    "pressure": {"baseline": 4.5, "unit": "bar", "noise_stddev": 0.05, "drift_stddev": 0.01,
                 "spike_probability": 0.015, "spike_magnitude": 1.2},
}

# (sensor_id, sensor_type) pairs -- must match backend/db/init/03-seed.sql.
SENSOR_IDS = [
    ("gas-01", "gas"),
    ("temp-01", "temperature"),
    ("pressure-01", "pressure"),
    ("gas-02", "gas"),
    ("temp-02", "temperature"),
    ("gas-03", "gas"),
    ("pressure-02", "pressure"),
]

# A spike's offset shrinks by this factor every tick, so a leak/fault
# looks like it rises then gradually fades rather than jumping and vanishing.
SPIKE_DECAY = 0.85

# Scripted demo scenarios (see app/demo.py) set a per-sensor target offset;
# each tick closes a fraction of the remaining gap, so a triggered hazard
# ramps instead of teleporting. The ramp is asymmetric on purpose:
# - UP is slow so the rising phase BELOW the critical threshold (z < 6,
#   where the time-to-critical countdown lives) lasts ~20s. At 0.2 the
#   sensors blew past z=6 in ~6s and judges never saw the countdown tick.
#   Score still reaches CRITICAL in ~15-20s (severity saturates at z >= 5).
# - DOWN is fast so "reset to calm" clears the stage in ~15s, not 90.
SCENARIO_RAMP_UP = 0.07
SCENARIO_RAMP_DOWN = 0.3


@dataclass
class SimulatedSensor:
    sensor_id: str
    sensor_type: str
    unit: str
    baseline: float
    noise_stddev: float
    drift_stddev: float
    spike_probability: float
    spike_magnitude: float
    _current_baseline: float = None
    _spike_offset: float = 0.0
    # Written by the MQTT control callback thread, read by the tick loop.
    # A bare float assignment is atomic under the GIL, so no lock is needed.
    scenario_target: float = 0.0
    _scenario_offset: float = 0.0

    def __post_init__(self):
        if self._current_baseline is None:
            self._current_baseline = self.baseline

    def tick(self) -> float:
        """Advance this sensor by one time step and return its new reading."""
        # Slow random walk: the "true" underlying value wanders a little
        # each tick, pulled gently back toward its resting baseline so it
        # doesn't drift off to an unrealistic extreme over a long demo.
        pull_to_baseline = (self.baseline - self._current_baseline) * 0.05
        self._current_baseline += random.gauss(0, self.drift_stddev) + pull_to_baseline

        if random.random() < self.spike_probability:
            self._spike_offset += self.spike_magnitude
        else:
            self._spike_offset *= SPIKE_DECAY

        # Scripted-scenario ramp toward the commanded target (0 when calm).
        rising = abs(self.scenario_target) > abs(self._scenario_offset)
        ramp = SCENARIO_RAMP_UP if rising else SCENARIO_RAMP_DOWN
        self._scenario_offset += (self.scenario_target - self._scenario_offset) * ramp

        measurement_noise = random.gauss(0, self.noise_stddev)
        return round(
            self._current_baseline + self._spike_offset + self._scenario_offset + measurement_noise,
            2,
        )


def build_sensors() -> list[SimulatedSensor]:
    sensors = []
    for sensor_id, sensor_type in SENSOR_IDS:
        defaults = TYPE_DEFAULTS[sensor_type]
        sensors.append(SimulatedSensor(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            unit=defaults["unit"],
            baseline=defaults["baseline"],
            noise_stddev=defaults["noise_stddev"],
            drift_stddev=defaults["drift_stddev"],
            spike_probability=defaults["spike_probability"],
            spike_magnitude=defaults["spike_magnitude"],
        ))
    return sensors
