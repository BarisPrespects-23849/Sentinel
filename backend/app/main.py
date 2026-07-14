"""FastAPI entry point for the SENTINEL backend.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import json
from pathlib import Path
from typing import Literal

import psycopg2
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents.graph import assess_zone
from app.compliance.coverage import coverage_summary
from app.db import get_connection
from app.demo import trigger_scenario
from app.geo import get_plant_geojson
from app.risk import engine
from app.risk.signals import list_zones
from app.risk.simulate import get_simulation_context, simulate_zone

app = FastAPI(
    title="SENTINEL API",
    description="AI-Powered Industrial Safety Intelligence Platform",
    version="0.1.0",
)

# The Vite dev server serves the frontend on this origin. Without this
# middleware, the browser blocks the frontend's fetch() calls to the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"service": "SENTINEL", "status": "online"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


def get_db():
    try:
        conn = get_connection()
    except psycopg2.OperationalError:
        # DB unreachable is an operational state, not a server bug: return
        # a clean 503 the frontend can message, not a raw stack-trace 500.
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        yield conn
    finally:
        conn.close()


@app.get("/risk/zones")
def get_all_zone_risks(conn=Depends(get_db)):
    zones = list_zones(conn)
    return [engine.score_zone(conn, z["zone_id"], z["name"]) for z in zones]


@app.get("/risk/zones/{zone_id}")
def get_zone_risk(zone_id: int, conn=Depends(get_db)):
    zones = {z["zone_id"]: z["name"] for z in list_zones(conn)}
    if zone_id not in zones:
        raise HTTPException(status_code=404, detail="Zone not found")
    return engine.score_zone(conn, zone_id, zones[zone_id])


@app.get("/agents/assess/{zone_id}")
def get_agent_assessment(zone_id: int, conn=Depends(get_db)):
    """Full multi-agent assessment: sensor + permit + maintenance fusion,
    via the LangGraph graph, vs. /risk/zones' sensor-only view."""
    try:
        return assess_zone(conn, zone_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/geo/plant")
def get_plant_geo(conn=Depends(get_db)):
    """Zone polygons + sensor points as GeoJSON, each zone tagged with its
    cheap sensor-only risk score/level for map coloring."""
    return get_plant_geojson(conn)


class SimulateRequest(BaseModel):
    """What-if slider values: sensor_type -> hypothetical reading."""

    zone_id: int
    values: dict[str, float]


@app.get("/risk/simulate/{zone_id}")
def get_simulate_context(zone_id: int, conn=Depends(get_db)):
    """Slider configuration for a zone: available sensor types with units,
    baselines, ranges, and current live values."""
    try:
        return get_simulation_context(conn, zone_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/risk/simulate")
def post_simulate(req: SimulateRequest, conn=Depends(get_db)):
    """Score hypothetical sensor values through the real risk engine --
    the exact same code path as live scoring."""
    unknown = set(req.values) - {"gas", "temperature", "pressure"}
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown sensor types: {sorted(unknown)}")
    try:
        return simulate_zone(conn, req.zone_id, req.values)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class ScenarioRequest(BaseModel):
    """Scripted demo scenario: 'compound' drives one zone's gas+temperature
    sensors to critical over ~30s; 'calm' returns every sensor to baseline."""

    scenario: Literal["compound", "calm"]
    zone_id: int | None = None


@app.post("/demo/scenario")
def post_demo_scenario(req: ScenarioRequest, conn=Depends(get_db)):
    """Inject a scripted scenario into the live simulator (via a retained
    MQTT control message), so the demo never depends on random noise."""
    if req.scenario == "compound" and req.zone_id is None:
        raise HTTPException(status_code=422, detail="zone_id is required for the compound scenario")
    try:
        return trigger_scenario(conn, req.scenario, req.zone_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except OSError:
        raise HTTPException(status_code=503, detail="MQTT broker unavailable")


@app.get("/compliance/coverage")
def get_compliance_coverage():
    """Regulatory coverage of the indexed corpus (read-only, no DB/LLM).
    Grouped by body with the honest primary (OISD, Factory Act) vs.
    mining-adjacency (DGMS) framing, and labeled a demonstration set."""
    return coverage_summary()


BENCHMARK_RESULTS_PATH = Path(__file__).resolve().parent / "benchmark" / "benchmark_results.json"


@app.get("/benchmark/results")
def get_benchmark_results():
    """Read-only: the offline detection-benchmark results (synthetic
    scenarios). Served straight from the JSON the harness wrote -- no
    scoring, DB, or LLM at request time. Numbers here trace to a real
    computed benchmark run and cannot drift from it."""
    if not BENCHMARK_RESULTS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Benchmark results not available -- run: python -m app.benchmark.run",
        )
    return json.loads(BENCHMARK_RESULTS_PATH.read_text())
