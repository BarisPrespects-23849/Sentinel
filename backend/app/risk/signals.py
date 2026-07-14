"""Extracts live per-zone signals from TimescaleDB for risk scoring."""

from app.simulator.sensors import TYPE_DEFAULTS

WINDOW_SECONDS = 60
MIN_READINGS_FOR_RATE = 2


def list_zones(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT zone_id, name FROM zones ORDER BY zone_id")
        return [{"zone_id": row[0], "name": row[1]} for row in cur.fetchall()]


def get_zone_signals(conn, zone_id: int) -> dict:
    """Returns {"per_sensor": [...], "by_type": {...}} for the given zone,
    using each sensor's readings from the last WINDOW_SECONDS.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.sensor_id, s.sensor_type, r.ts, r.value
            FROM sensors s
            JOIN sensor_readings r ON r.sensor_id = s.sensor_id
            WHERE s.zone_id = %s AND r.ts > now() - make_interval(secs => %s)
            ORDER BY s.sensor_id, r.ts ASC
            """,
            (zone_id, WINDOW_SECONDS),
        )
        rows = cur.fetchall()

    readings_by_sensor: dict[str, list[tuple]] = {}
    for sensor_id, sensor_type, ts, value in rows:
        readings_by_sensor.setdefault(sensor_id, {"sensor_type": sensor_type, "points": []})
        readings_by_sensor[sensor_id]["points"].append((ts, value))

    per_sensor = []
    for sensor_id, data in readings_by_sensor.items():
        sensor_type = data["sensor_type"]
        points = data["points"]
        defaults = TYPE_DEFAULTS[sensor_type]

        latest_ts, latest_value = points[-1]
        z = (latest_value - defaults["baseline"]) / defaults["noise_stddev"]

        if len(points) >= MIN_READINGS_FOR_RATE:
            oldest_ts, oldest_value = points[0]
            elapsed = (latest_ts - oldest_ts).total_seconds()
            rate_raw = (latest_value - oldest_value) / elapsed if elapsed > 0 else 0.0
        else:
            rate_raw = 0.0
        rate_z = rate_raw / defaults["noise_stddev"]

        per_sensor.append({
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "unit": defaults["unit"],
            "latest_value": latest_value,
            "z": z,
            "rate_z": rate_z,
        })

    # If a zone has two sensors of the same type, the worse (higher z) one
    # represents that type in the feature vector -- risk should track the
    # worst signal present, not an average that could dilute it.
    by_type: dict[str, dict] = {}
    for s in per_sensor:
        existing = by_type.get(s["sensor_type"])
        if existing is None or s["z"] > existing["z"]:
            by_type[s["sensor_type"]] = {"z": s["z"], "rate_z": s["rate_z"]}

    return {"per_sensor": per_sensor, "by_type": by_type}
