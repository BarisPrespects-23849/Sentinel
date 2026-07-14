"""What-if simulation: scores hypothetical sensor values for a zone
through the EXACT same engine as live scoring (engine.score_signals).

The demo story this enables: drag gas up alone and the score stays modest
(single-sensor anomaly); add temperature and the compound multiplier + ML
model fire together. That contrast IS the "compound risk detection vs.
single-sensor baselines" rubric criterion, made physical.

Simulated readings are treated as steady-state (rate_z = 0): a slider
position says nothing about how fast the value is moving, so we don't
invent a trend -- and consequently no time-to-critical countdown is shown
for simulations.
"""

from app.risk import engine
from app.simulator.sensors import TYPE_DEFAULTS

# Slider bounds per sensor type, chosen to give demo headroom well past
# the critical threshold while staying physically plausible.
SLIDER_RANGE = {
    "gas": {"min": 0.0, "max": 60.0, "step": 0.5},
    "temperature": {"min": 20.0, "max": 60.0, "step": 0.5},
    "pressure": {"min": 0.0, "max": 10.0, "step": 0.1},
}


def _zone_types(conn, zone_id: int) -> dict[str, str]:
    """{sensor_type: representative sensor_id} for the zone's sensors."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sensor_type, min(sensor_id) FROM sensors"
            " WHERE zone_id = %s GROUP BY sensor_type",
            (zone_id,),
        )
        return dict(cur.fetchall())


def get_simulation_context(conn, zone_id: int) -> dict:
    """Everything the frontend needs to build the sliders: which sensor
    types exist in this zone, their units/baselines/ranges, and the most
    recent live value to initialize each slider with."""
    types = _zone_types(conn, zone_id)
    if not types:
        raise ValueError(f"Zone {zone_id} not found or has no sensors")

    controls = []
    with conn.cursor() as cur:
        for sensor_type, sensor_id in sorted(types.items()):
            defaults = TYPE_DEFAULTS[sensor_type]
            cur.execute(
                "SELECT value FROM sensor_readings WHERE sensor_id = %s ORDER BY ts DESC LIMIT 1",
                (sensor_id,),
            )
            row = cur.fetchone()
            controls.append({
                "sensor_type": sensor_type,
                "unit": defaults["unit"],
                "baseline": defaults["baseline"],
                "current_value": row[0] if row else defaults["baseline"],
                **SLIDER_RANGE[sensor_type],
            })
    return {"zone_id": zone_id, "controls": controls}


def simulate_zone(conn, zone_id: int, values: dict[str, float]) -> dict:
    """Score hypothetical readings for a zone. `values` maps sensor_type
    to the slider value; types not provided fall back to their baseline."""
    types = _zone_types(conn, zone_id)
    if not types:
        raise ValueError(f"Zone {zone_id} not found or has no sensors")

    per_sensor = []
    by_type = {}
    for sensor_type in sorted(types):
        defaults = TYPE_DEFAULTS[sensor_type]
        value = float(values.get(sensor_type, defaults["baseline"]))
        # Server-side clamp to the published slider range: the API must
        # not trust clients to respect bounds (a POST can send anything).
        bounds = SLIDER_RANGE[sensor_type]
        value = max(bounds["min"], min(bounds["max"], value))
        z = (value - defaults["baseline"]) / defaults["noise_stddev"]
        per_sensor.append({
            "sensor_id": f"simulated {sensor_type}",
            "sensor_type": sensor_type,
            "unit": defaults["unit"],
            "latest_value": round(value, 2),
            "z": z,
            "rate_z": 0.0,
        })
        by_type[sensor_type] = {"z": z, "rate_z": 0.0}

    result = engine.score_signals(per_sensor, by_type)
    # Steady-state assumption -> no trend, no countdown (see module docstring).
    result["time_to_critical_seconds"] = None
    return {"zone_id": zone_id, "simulated": True, **result}
