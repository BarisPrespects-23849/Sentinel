"""MQTT-to-TimescaleDB ingest service.

Subscribes to every sensor's reading topic and writes each message into
the sensor_readings hypertable. Runs as a separate process from both the
simulator (publisher) and the FastAPI app, communicating only through MQTT
and Postgres -- exactly how a real deployment would separate "device
telemetry ingestion" from "device simulation" and "API serving."

Run with:
    python -m app.ingest.subscriber
"""

import json
import logging
import os
import time

import paho.mqtt.client as mqtt
import psycopg2

from app.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ingest] %(message)s")
logger = logging.getLogger(__name__)

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
READING_TOPIC_FILTER = "sentinel/sensors/+/reading"
DB_RETRY_SECONDS = 5

# The connection is owned by _store() and re-established on failure, so a
# database restart mid-run costs a few readings, not the whole service.
_conn = None


def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        conn = get_connection()
        conn.autocommit = True
        _conn = conn
        logger.info("Connected to Postgres")
    return _conn


def _store(payload: dict):
    global _conn
    try:
        with _get_conn().cursor() as cur:
            cur.execute(
                "INSERT INTO sensor_readings (ts, sensor_id, value) VALUES (%s, %s, %s)",
                (payload["ts"], payload["sensor_id"], payload["value"]),
            )
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        # Connection died (e.g. Postgres restarted). Drop it so the next
        # message reconnects; retry this write once after a short pause.
        logger.warning("Postgres connection lost -- reconnecting in %ss", DB_RETRY_SECONDS)
        _conn = None
        time.sleep(DB_RETRY_SECONDS)
        with _get_conn().cursor() as cur:
            cur.execute(
                "INSERT INTO sensor_readings (ts, sensor_id, value) VALUES (%s, %s, %s)",
                (payload["ts"], payload["sensor_id"], payload["value"]),
            )


def on_connect(client, userdata, connect_flags, reason_code, properties):
    logger.info("Connected to MQTT broker (%s)", reason_code)
    client.subscribe(READING_TOPIC_FILTER)


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
        _store(payload)
        logger.info("Stored %s = %s", payload["sensor_id"], payload["value"])
    except Exception:
        logger.exception("Failed to store message on topic %s", message.topic)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    # Retry initial broker connection so start order doesn't matter (e.g.
    # this service starting before Docker finishes bringing up Mosquitto).
    # Once connected, loop_forever() handles broker reconnects itself.
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT)
            break
        except OSError:
            logger.warning("MQTT broker unreachable -- retrying in %ss", DB_RETRY_SECONDS)
            time.sleep(DB_RETRY_SECONDS)
    logger.info("Listening on %s at %s:%s", READING_TOPIC_FILTER, MQTT_HOST, MQTT_PORT)
    client.loop_forever()


if __name__ == "__main__":
    main()
