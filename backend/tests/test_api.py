"""API integration tests via FastAPI's TestClient, against the dev
database (Docker Compose must be up). The LLM-backed /agents/assess happy
path is deliberately NOT exercised here (cost + external dependency) --
it's covered by the Playwright end-to-end flow instead; only its cheap
error path is tested."""

from app.risk.simulate import SLIDER_RANGE


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_risk_zones_lists_all_seeded_zones(client):
    res = client.get("/risk/zones")
    assert res.status_code == 200
    zones = res.json()
    assert {z["zone_name"] for z in zones} == {
        "Compressor House",
        "Storage Tank Farm",
        "Pipeline Corridor",
    }
    for zone in zones:
        assert zone["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN")


def test_risk_zone_unknown_404(client):
    assert client.get("/risk/zones/999").status_code == 404


def test_geo_plant_shape(client):
    res = client.get("/geo/plant")
    assert res.status_code == 200
    data = res.json()
    assert len(data["zones"]["features"]) == 3
    assert len(data["sensors"]["features"]) == 7
    for feature in data["zones"]["features"]:
        assert feature["geometry"]["type"] == "Polygon"
        assert "risk_level" in feature["properties"]
        # Additive fields: always present with stable types.
        props = feature["properties"]
        assert isinstance(props["active_permits"], list)
        assert isinstance(props["has_elevated_sensors"], bool)
        assert isinstance(props["compound"], bool)
        # compound is exactly permit AND elevated -- never one alone.
        assert props["compound"] == (
            bool(props["active_permits"]) and props["has_elevated_sensors"]
        )
    for feature in data["sensors"]["features"]:
        assert feature["geometry"]["type"] == "Point"
        lng, lat = feature["geometry"]["coordinates"]
        assert 77 < lng < 78 and 12 < lat < 14
        # Additive per-sensor state: elevated flag always present; z is a
        # number when there are recent readings, else None.
        sp = feature["properties"]
        assert isinstance(sp["elevated"], bool)
        assert sp["z"] is None or isinstance(sp["z"], (int, float))


def test_simulate_context_shape(client):
    res = client.get("/risk/simulate/1")
    assert res.status_code == 200
    controls = res.json()["controls"]
    assert {c["sensor_type"] for c in controls} == {"gas", "temperature", "pressure"}
    for control in controls:
        assert control["min"] < control["max"]
        assert "unit" in control and "baseline" in control


def test_simulate_context_unknown_zone_404(client):
    assert client.get("/risk/simulate/999").status_code == 404


def test_simulate_single_vs_compound(client):
    single = client.post(
        "/risk/simulate",
        json={"zone_id": 1, "values": {"gas": 30, "temperature": 36, "pressure": 4.5}},
    ).json()
    compound = client.post(
        "/risk/simulate",
        json={"zone_id": 1, "values": {"gas": 30, "temperature": 40, "pressure": 4.5}},
    ).json()
    assert single["risk_level"] == "LOW"
    assert single["ml_score"] < 20
    assert compound["risk_level"] in ("HIGH", "CRITICAL")
    assert compound["ml_score"] > 80


def test_simulate_clamps_out_of_range_values(client):
    # Absurd inputs must clamp to the published slider range, not blow up.
    res = client.post(
        "/risk/simulate",
        json={"zone_id": 1, "values": {"gas": 1e9, "temperature": -500, "pressure": 4.5}},
    )
    assert res.status_code == 200
    body = res.json()
    gas_signal = next(
        s for s in body["contributing_signals"] if s.get("sensor_type") == "gas"
    )
    assert f"{SLIDER_RANGE['gas']['max']}" in gas_signal["description"]


def test_simulate_unknown_sensor_type_422(client):
    res = client.post(
        "/risk/simulate", json={"zone_id": 1, "values": {"radiation": 5}}
    )
    assert res.status_code == 422


def test_simulate_malformed_body_422(client):
    res = client.post("/risk/simulate", json={"zone_id": "not-a-number"})
    assert res.status_code == 422


def test_simulate_unknown_zone_404(client):
    res = client.post("/risk/simulate", json={"zone_id": 999, "values": {"gas": 10}})
    assert res.status_code == 404


def test_agents_assess_unknown_zone_404(client):
    assert client.get("/agents/assess/999").status_code == 404
