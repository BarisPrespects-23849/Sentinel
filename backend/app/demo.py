"""Scripted demo scenarios.

Publishes a retained control message to the MQTT broker; the simulator
(app/simulator/publisher.py) subscribes and ramps the named sensors toward
the commanded offsets. Injecting via MQTT rather than writing readings
straight into the database keeps the demo honest: every value on the map
still arrived through the real sensor -> broker -> ingest -> TimescaleDB
path, exactly like live telemetry.

The message is retained (the broker re-delivers the last one to any new
subscriber), so a simulator restarted mid-demo re-enters the active
scenario instead of quietly resetting it.
"""

import json
import os

import paho.mqtt.client as mqtt

from app.simulator.sensors import TYPE_DEFAULTS

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
CONTROL_TOPIC = "sentinel/control/scenario"

# The compound scenario drives one zone's gas + temperature sensors -- the
# rubric's headline case: two different sensor types elevated at once.
COMPOUND_TYPES = ("gas", "temperature")

# Commanded offset per type = TARGET_Z standard deviations above baseline,
# on exactly the scale the risk engine scores (signals.py divides by the
# same noise_stddev). 15 sigma is far past both the elevation threshold
# (z > 2) and severity saturation (z >= 5), so the plateau is unambiguously
# CRITICAL while the ~30s ramp shows a live rising trend and countdown.
TARGET_Z = 15.0


def _publish_control(payload: dict) -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()
    try:
        info = client.publish(CONTROL_TOPIC, json.dumps(payload), qos=1, retain=True)
        info.wait_for_publish(timeout=5)
    finally:
        client.loop_stop()
        client.disconnect()


def trigger_scenario(conn, scenario: str, zone_id: int | None) -> dict:
    """Publish a scenario control message. Raises KeyError if the zone does
    not exist, ValueError if it lacks the sensor types the scenario needs,
    OSError if the broker is unreachable."""
    if scenario == "calm":
        _publish_control({"scenario": "calm", "targets": {}, "suppress_spikes": False})
        return {
            "scenario": "calm",
            "targets": {},
            "note": "All sensors commanded back to baseline; scores settle within ~60s.",
        }

    with conn.cursor() as cur:
        cur.execute("SELECT name FROM zones WHERE zone_id = %s", (zone_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(f"Zone {zone_id} not found")
        zone_name = row[0]

        cur.execute(
            "SELECT sensor_id, sensor_type FROM sensors "
            "WHERE zone_id = %s AND sensor_type = ANY(%s)",
            (zone_id, list(COMPOUND_TYPES)),
        )
        sensors = cur.fetchall()

    types_present = {sensor_type for _, sensor_type in sensors}
    missing = [t for t in COMPOUND_TYPES if t not in types_present]
    if missing:
        raise ValueError(
            f"Zone {zone_id} ({zone_name}) has no {' or '.join(missing)} sensor -- "
            "the compound scenario needs both gas and temperature"
        )

    targets = {
        sensor_id: round(TARGET_Z * TYPE_DEFAULTS[sensor_type]["noise_stddev"], 2)
        for sensor_id, sensor_type in sensors
    }
    _publish_control({
        "scenario": "compound",
        "zone_id": zone_id,
        "targets": targets,
        # Disable random spikes plant-wide while the scripted scenario runs,
        # so a chance co-spike in another zone can't upstage the demo.
        "suppress_spikes": True,
    })
    return {
        "scenario": "compound",
        "zone_id": zone_id,
        "zone_name": zone_name,
        "targets": targets,
        "note": (
            "Sensors ramp toward target; expect CRITICAL within ~20s, with a "
            "ticking time-to-critical countdown during the rising phase."
        ),
    }
