# SENTINEL

AI-Powered Industrial Safety Intelligence Platform for Zero-Harm Operations.

Built for the ET AI Hackathon 2026, Problem Statement 1.

## What it does

Industrial sites run gas sensors, work permits, and maintenance records in separate
systems that nobody cross-references in real time. SENTINEL fuses all of them
through a multi-agent AI system and detects **compound risk** — dangerous
combinations of individually-normal readings — before a fatality occurs. It
explains *why* it flagged something with a full causal chain, shows a countdown
to critical threshold, and lets you drag a "what-if" slider to simulate changing
conditions and watch the risk score update live.

## Architecture

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn (Python) |
| Agent orchestration | LangGraph |
| LLM (most agents) | Claude API |
| LLM (Compliance Agent only) | Gemini API (`gemini-3.5-flash`) |
| Time-series DB | TimescaleDB (Postgres extension) |
| Geospatial | PostGIS + deck.gl |
| Knowledge graph | Neo4j |
| Vector DB | ChromaDB |
| Streaming | MQTT (simulated IoT) |
| Frontend | React + Tailwind + deck.gl |
| Containerization | Docker + Docker Compose |

Multi-agent graph (LangGraph supervisor pattern): Orchestrator → Sensor Agent,
Permit Agent, Maintenance Agent, Vision Agent, Compliance Agent, Pattern Agent,
Risk Synthesis Agent.

**Note on the Compliance Agent's LLM:** the original plan used Claude for every
agent. The Compliance Agent specifically uses Gemini instead (`gemini-3.5-flash`)
-- a deliberate call made mid-build, not an oversight. Every other agent
(Sensor, Permit, Maintenance, and eventually Risk Synthesis's narrative
generation) still assumes Claude per the original plan; only this one RAG-based
narrative-generation call was pointed at Gemini. If asked about this in judging,
be upfront that it's a deliberate one-off substitution, not a full-stack
migration off Claude.

## Running locally

### One-command stack (recommended)

```bash
cp .env.example .env   # then edit POSTGRES_PASSWORD, add GEMINI_API_KEY
docker compose up -d --build
cd frontend && npm install && npm run dev
```

That starts everything except the frontend dev server: the database
(TimescaleDB + PostGIS), the MQTT broker, the FastAPI backend on :8000,
the sensor simulator, and the ingest worker. The backend image bakes in
the trained ML model and the ChromaDB regulation index at build time, so
the demo has no runtime internet dependency beyond basemap tiles and the
optional Gemini narrative. Dashboard: http://localhost:5173. See DEMO.md
for the rehearsed demo script and `./scripts/demo_reset.sh` for one-shot
demo staging.

The sections below run the application pieces natively instead (useful
for development -- `uvicorn --reload` beats rebuilding an image). The two
workflows share the same db/mqtt containers; just don't run both the
`api` container and a local uvicorn at once (both want :8000).

### Database

```bash
cp .env.example .env   # then edit POSTGRES_PASSWORD
docker compose up -d db mqtt
```

Runs Postgres 16 with TimescaleDB (time-series hypertables) and PostGIS
(geospatial types/queries) both enabled, on `localhost:55432`. Data persists
in the `sentinel_db_data` Docker volume across restarts. Also runs an MQTT
broker (Eclipse Mosquitto) on `localhost:1883` for sensor telemetry.

**Why port 55432, not 5432:** macOS machines often run a native Postgres
(Homebrew/Postgres.app) that auto-starts on boot and binds localhost:5432.
When both listen, connections silently reach the native server instead of
the container and fail with "role sentinel does not exist". A non-default
port avoids the collision entirely.

Schema (`zones`, `sensors`, `sensor_readings` hypertable) and seed data
(3 zones, 7 sensors) load automatically the first time the `db` container
starts, from `backend/db/init/*.sql`.

### Simulated sensors

With the database and MQTT broker running, and the backend venv set up
(see below), run these two in separate terminals:

```bash
cd backend && source venv/bin/activate
python -m app.simulator.publisher   # generates + publishes fake readings
python -m app.ingest.subscriber     # subscribes + writes them to TimescaleDB
```

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs for the interactive API docs.

The risk engine's ML layer needs a trained model at `backend/app/risk/model.joblib`
(gitignored, regenerated locally). It auto-trains on first API request if missing,
or train it explicitly:

```bash
python -m app.risk.train_model
```

`GET /risk/zones` and `GET /risk/zones/{zone_id}` return the current hybrid
risk score per zone (rules + ML blended) with a full `contributing_signals`
explanation trail.

`GET /agents/assess/{zone_id}` runs the full LangGraph multi-agent graph
(Orchestrator -> Sensor + Maintenance Agents in parallel -> Permit +
Compliance Agents, which both consume the Sensor Agent's output -> Risk
Synthesis) and returns a fused score that also accounts for
active work permits, sensor calibration status, and grounded regulatory
citations -- compare its output against `/risk/zones/{zone_id}` to see what
multi-source fusion adds over the sensor-only baseline. Vision and Pattern
Agents are designed but not yet wired in (see `app/agents/graph.py`) -- they
need simulated CCTV data and the Neo4j knowledge graph respectively, neither
built yet.

### Compliance Agent (RAG)

Needs `GEMINI_API_KEY` in `.env` (get one from Google AI Studio). The
regulatory corpus (`backend/app/compliance/corpus.py`) is a small, real,
cited sample -- excerpts from The Factories Act 1948 and summaries of
OISD-STD-105 / OISD-STD-114 -- sized for this demo's permit types, **not** a
complete or authoritative compliance database. Build the vector index once:

```bash
python -m app.compliance.ingest
```

The Compliance Agent only calls the LLM when a zone has an active permit or
an elevated sensor reading -- a fully calm zone costs nothing. Its
contribution is purely explanatory (a grounded, cited narrative), not a
numeric risk bonus, to avoid double-counting with the Permit Agent's scoring.

**Quota resilience** (free-tier Gemini quotas are small and per-model,
per-day -- observed 20/day on `gemini-3.5-flash`): successful narratives
are cached in-memory for 10 minutes per situation; 429s are never retried
(a daily quota won't reset between attempts); on quota exhaustion the agent
falls back to `gemini-3.1-flash-lite` (separate quota), and if everything
fails it degrades to an explicit "narrative unavailable" signal with the
retrieved citations intact -- the assessment itself never fails because of
the LLM. A missing `GEMINI_API_KEY` disables the narrative but never
prevents the backend from starting.

### Backend tests

```bash
cd backend && source venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/
```

Unit tests cover the rules layer and hybrid engine (including the
compound-vs-single-sensor property the judging rubric scores, and a
regression test for plateaued-hazard detection). API tests run against the
dev database via FastAPI's TestClient and cover validation, clamping, 404s,
and the simulate endpoints.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173. The dashboard shows the live plant map (deck.gl
over a free CARTO dark basemap -- no API key needed), a zone "annunciator
rail" on the left, and a detail panel that runs the full multi-agent
assessment when you select a zone.

Design system: tokens live in `src/index.css` (Tailwind v4 `@theme` block).
The color philosophy follows industrial HMI practice (ISA-101): normal state
renders in muted steel, and amber/orange/red appear only as alarm semantics.
Fonts (Barlow Condensed, IBM Plex Sans/Mono) are self-hosted via
`@fontsource` so the demo doesn't depend on Google Fonts at the venue.

### What-if simulation

Select a zone, then drag the sliders in the detail panel to test
hypothetical sensor readings. Simulated values are scored by the **same
engine code path as live data** (`engine.score_signals`) via:

- `GET /risk/simulate/{zone_id}` -- slider configuration (types, units,
  baselines, ranges, current live values)
- `POST /risk/simulate` -- `{zone_id, values: {gas, temperature, pressure}}`
  returns the hybrid score + causal signals

The demo contrast to show judges: push gas up alone (single-sensor anomaly,
modest score, ML near 0%) then add temperature (compound multiplier + ML
fire together, score goes critical). Simulated readings are steady-state
(no invented trend), so no time-to-critical countdown is shown for them.

### Verifying the UI (headless browser)

```bash
cd frontend
node scripts/screenshot.mjs out.png           # screenshot the dashboard
node scripts/screenshot.mjs out.png 1         # click zone 1, wait for the
                                              # full assessment, screenshot
node scripts/screenshot.mjs out.png 1 whatif  # also drive the what-if
                                              # sliders to a compound state
```

Uses Playwright (installed as a dev dependency; run
`npx playwright install chromium` once). A Playwright MCP server is also
registered in `.mcp.json` for interactive browser control from Claude Code.

### Scripted demo scenarios

The demo never has to depend on random sensor noise. `POST /demo/scenario`
publishes a **retained** MQTT control message that the simulator obeys:

```bash
# Drive one zone's gas + temperature sensors to critical: ~20s of rising
# readings (with a live ticking time-to-critical countdown), then CRITICAL
curl -X POST localhost:8000/demo/scenario -H "Content-Type: application/json" \
     -d '{"scenario": "compound", "zone_id": 1}'

# Return every sensor to baseline (fast decay, settles in well under a minute)
curl -X POST localhost:8000/demo/scenario -H "Content-Type: application/json" \
     -d '{"scenario": "calm"}'
```

The same controls live at the bottom of the dashboard's zone rail ("Demo
scenario": select a zone, then Inject compound / Reset to calm). While a
scripted scenario is active, random spikes are suppressed plant-wide and
any in-flight spike is cleared, so a chance anomaly in another zone cannot
upstage the scripted narrative. Because the control message is retained by
the broker, a restarted simulator immediately re-enters the active
scenario. Injection goes through MQTT -- not direct DB writes -- so every
value on the map still traveled the real sensor -> broker -> ingest ->
TimescaleDB path.

### Demo freshness

Seeded permits use relative timestamps and expire ~4 hours after the
database volume is created. To re-arm the hot-work permit before a demo:

```sql
UPDATE permits SET valid_from = now() - interval '2 hours',
                   valid_until = now() + interval '4 hours'
WHERE permit_type = 'hot_work' AND zone_id = 1;
```
