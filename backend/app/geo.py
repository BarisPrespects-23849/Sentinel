"""Converts zones/sensors PostGIS geometry into GeoJSON for the frontend map.

Zone risk scores here are the cheap, sensor-only hybrid score from
app.risk.engine (Milestone 4) -- no permits/maintenance/compliance, no LLM
calls. This is what colors the map on every poll. The full multi-agent
assessment (with the LLM-backed compliance narrative) is fetched
separately, per zone, only when a judge clicks into a zone -- see
GET /agents/assess/{zone_id} in main.py.
"""

import json

from app.risk import engine
from app.risk.features import ELEVATED_Z_THRESHOLD
from app.risk.signals import get_zone_signals, list_zones


def get_plant_geojson(conn) -> dict:
    zones = list_zones(conn)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT zone_id, ST_AsGeoJSON(boundary),"
            " ST_X(ST_Centroid(boundary)), ST_Y(ST_Centroid(boundary))"
            " FROM zones"
        )
        rows = cur.fetchall()
        zone_geometry = {r[0]: r[1] for r in rows}
        zone_centroid = {r[0]: (r[2], r[3]) for r in rows}

        cur.execute(
            "SELECT sensor_id, zone_id, sensor_type, unit, ST_AsGeoJSON(location) FROM sensors"
        )
        sensor_rows = cur.fetchall()

        # Active work permits per zone -- same currently-valid definition the
        # Permit/Compliance agents use. Read-only; surfaced so the map can
        # show the permit spatially, not only in the detail panel.
        cur.execute(
            "SELECT zone_id, permit_type FROM permits"
            " WHERE status = 'active' AND now() BETWEEN valid_from AND valid_until"
        )
        active_permits_by_zone: dict[int, set] = {}
        for zid, permit_type in cur.fetchall():
            active_permits_by_zone.setdefault(zid, set()).add(permit_type)

    # Per-sensor live state, so the map can show WHICH sensors are driving a
    # zone's risk (elevated vs normal), tracing the score to specific sensor
    # locations. Read-only; "elevated" uses the same z-threshold as the rules
    # layer. Sensors with no recent readings simply stay absent here.
    sensor_state: dict[str, dict] = {}
    for zone in zones:
        for s in get_zone_signals(conn, zone["zone_id"])["per_sensor"]:
            sensor_state[s["sensor_id"]] = {
                "z": round(s["z"], 1),
                "elevated": s["z"] > ELEVATED_Z_THRESHOLD,
            }

    zone_features = []
    for zone in zones:
        risk = engine.score_zone(conn, zone["zone_id"], zone["name"])
        permits = sorted(active_permits_by_zone.get(zone["zone_id"], set()))
        # rule_score > 0 means at least one sensor crossed the elevation
        # threshold -- the SAME "elevated" test the Permit Agent uses for its
        # co-occurrence check. "compound" is therefore the exact condition the
        # agent scores: a hazardous permit overlapping elevated sensors.
        has_elevated = (risk.get("rule_score") or 0) > 0
        zone_features.append({
            "type": "Feature",
            "geometry": json.loads(zone_geometry[zone["zone_id"]]),
            "properties": {
                "zone_id": zone["zone_id"],
                "name": zone["name"],
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
                # Label anchor for the frontend's TextLayer.
                "label_lng": zone_centroid[zone["zone_id"]][0],
                "label_lat": zone_centroid[zone["zone_id"]][1],
                # Additive: active permit types in this zone (may be empty).
                "active_permits": permits,
                "has_elevated_sensors": has_elevated,
                # The compound-risk condition, made spatial: a permit AND
                # elevated sensors co-occurring in the same zone.
                "compound": has_elevated and bool(permits),
            },
        })

    sensor_features = [
        {
            "type": "Feature",
            "geometry": json.loads(geojson_str),
            "properties": {
                "sensor_id": sensor_id,
                "zone_id": zone_id,
                "sensor_type": sensor_type,
                "unit": unit,
                # Additive live state (default calm when no recent readings).
                "elevated": sensor_state.get(sensor_id, {}).get("elevated", False),
                "z": sensor_state.get(sensor_id, {}).get("z"),
            },
        }
        for sensor_id, zone_id, sensor_type, unit, geojson_str in sensor_rows
    ]

    return {
        "zones": {"type": "FeatureCollection", "features": zone_features},
        "sensors": {"type": "FeatureCollection", "features": sensor_features},
    }
