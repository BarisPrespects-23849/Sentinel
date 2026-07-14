"""Simulated IoT sensor publisher.

Ticks every sensor on an interval and publishes each reading to the MQTT
broker, mimicking real sensor hardware reporting over the network.

Run with:
    python -m app.simulator.publisher
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from app.simulator.sensors import TYPE_DEFAULTS, build_sensors

logging.basicConfig(level=logging.INFO, format="%(asctime)s [publisher] %(message)s")
logger = logging.getLogger(__name__)

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
TICK_INTERVAL_SECONDS = float(os.environ.get("TICK_INTERVAL_SECONDS", "3"))

# Scripted demo scenarios arrive on this topic as retained messages (see
# app/demo.py), so a restarted simulator immediately re-enters whatever
# scenario is currently active instead of silently resetting the demo.
CONTROL_TOPIC = "sentinel/control/scenario"


def topic_for(sensor_id: str) -> str:
    return f"sentinel/sensors/{sensor_id}/reading"


def apply_scenario(sensors, payload: dict) -> None:
    """Set each sensor's scenario target from a control message. Sensors not
    named in the message are commanded back to 0, so every control message
    fully describes the desired plant state -- no leftover offsets.

    Scripted scenarios also set suppress_spikes: random spikes anywhere in
    the plant are disabled and any in-flight spike is cleared, so a chance
    co-spike in an untargeted zone can't upstage the scripted narrative.
    'Reset to calm' restores natural spike behavior."""
    targets = payload.get("targets") or {}
    suppress = bool(payload.get("suppress_spikes"))
    for sensor in sensors:
        sensor.scenario_target = float(targets.get(sensor.sensor_id, 0.0))
        sensor.spike_probability = (
            0.0 if suppress else TYPE_DEFAULTS[sensor.sensor_type]["spike_probability"]
        )
        # Every scenario transition starts from a clean slate.
        sensor._spike_offset = 0.0
    logger.info("Scenario '%s' applied (suppress_spikes=%s): %s",
                payload.get("scenario", "?"), suppress, targets or "all calm")


def make_on_message(sensors):
    def on_message(client, userdata, msg):
        try:
            apply_scenario(sensors, json.loads(msg.payload))
        except (ValueError, TypeError):
            logger.warning("Ignoring malformed control message: %r", msg.payload[:200])
    return on_message


def main():
    sensors = build_sensors()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = make_on_message(sensors)
    client.connect(MQTT_HOST, MQTT_PORT)
    client.subscribe(CONTROL_TOPIC, qos=1)
    client.loop_start()
    logger.info("Connected to MQTT broker at %s:%s, publishing %d sensors every %.1fs",
                MQTT_HOST, MQTT_PORT, len(sensors), TICK_INTERVAL_SECONDS)

    try:
        while True:
            for sensor in sensors:
                value = sensor.tick()
                payload = json.dumps({
                    "sensor_id": sensor.sensor_id,
                    "sensor_type": sensor.sensor_type,
                    "unit": sensor.unit,
                    "value": value,
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
                client.publish(topic_for(sensor.sensor_id), payload)
                logger.info("%s = %s %s", sensor.sensor_id, value, sensor.unit)
            time.sleep(TICK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Stopping publisher")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
