"""Tests for the scripted demo-scenario endpoint (POST /demo/scenario).

The MQTT publish is monkeypatched out so these tests exercise the API
contract (validation, zone resolution, target computation) without
needing a running broker -- the end-to-end MQTT path is covered by the
manual demo-verification step instead.
"""

import app.demo as demo
from app.simulator.sensors import TYPE_DEFAULTS


def _capture_publishes(monkeypatch):
    published = []
    monkeypatch.setattr(demo, "_publish_control", published.append)
    return published


def test_compound_scenario_targets_gas_and_temperature(client, monkeypatch):
    published = _capture_publishes(monkeypatch)

    res = client.post("/demo/scenario", json={"scenario": "compound", "zone_id": 1})
    assert res.status_code == 200
    body = res.json()

    assert body["scenario"] == "compound"
    assert body["zone_id"] == 1
    # Zone 1 (Compressor House) seeds gas-01 + temp-01 (and pressure-01,
    # which the compound scenario must NOT touch).
    assert set(body["targets"]) == {"gas-01", "temp-01"}

    # Offsets must be TARGET_Z sigmas on the engine's own scale.
    assert body["targets"]["gas-01"] == round(
        demo.TARGET_Z * TYPE_DEFAULTS["gas"]["noise_stddev"], 2
    )
    assert body["targets"]["temp-01"] == round(
        demo.TARGET_Z * TYPE_DEFAULTS["temperature"]["noise_stddev"], 2
    )

    # Exactly one control message, carrying the same targets, with random
    # spikes suppressed so nothing can upstage the scripted scenario.
    assert len(published) == 1
    assert published[0]["scenario"] == "compound"
    assert published[0]["targets"] == body["targets"]
    assert published[0]["suppress_spikes"] is True


def test_calm_scenario_clears_all_targets(client, monkeypatch):
    published = _capture_publishes(monkeypatch)

    res = client.post("/demo/scenario", json={"scenario": "calm"})
    assert res.status_code == 200
    assert res.json()["targets"] == {}
    assert published == [{"scenario": "calm", "targets": {}, "suppress_spikes": False}]


def test_compound_requires_zone_id(client, monkeypatch):
    published = _capture_publishes(monkeypatch)
    res = client.post("/demo/scenario", json={"scenario": "compound"})
    assert res.status_code == 422
    assert published == []


def test_compound_unknown_zone_404(client, monkeypatch):
    published = _capture_publishes(monkeypatch)
    res = client.post("/demo/scenario", json={"scenario": "compound", "zone_id": 999})
    assert res.status_code == 404
    assert published == []


def test_compound_zone_without_temperature_400(client, monkeypatch):
    published = _capture_publishes(monkeypatch)
    # Zone 3 (Pipeline Corridor) seeds gas + pressure but no temperature.
    res = client.post("/demo/scenario", json={"scenario": "compound", "zone_id": 3})
    assert res.status_code == 400
    assert "temperature" in res.json()["detail"]
    assert published == []


def test_unknown_scenario_name_422(client):
    res = client.post("/demo/scenario", json={"scenario": "meltdown", "zone_id": 1})
    assert res.status_code == 422
