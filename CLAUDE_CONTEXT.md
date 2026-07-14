# SENTINEL — Project Context for Claude Code

## Who I am
I am a CS student with zero knowledge of the specific technologies used in this project (FastAPI, Docker, LangGraph, PostGIS, RAG, etc.). I need every new technology explained before it is used. Keep explanations clear but do not simplify the project itself.

## What we are building
**SENTINEL** — An AI-Powered Industrial Safety Intelligence Platform for Zero-Harm Operations.

Built for the ET AI Hackathon 2026, Problem Statement 1.

### Core idea (plain English)
A factory has gas sensors, work permits, and maintenance records all in separate systems. Nobody cross-references them in real time. SENTINEL fuses all of them through a multi-agent AI system and detects COMPOUND RISK — dangerous combinations of individually-normal readings — before a fatality occurs. It explains WHY it flagged something (full causal chain), shows a countdown to critical threshold, and lets a judge drag a "what-if" slider to simulate changing conditions and watch the risk score update live.

### Why this wins
The judging rubric explicitly scores "compound risk detection accuracy versus single-sensor baselines." SENTINEL is architecturally designed around that exact metric. The what-if slider gives judges something to physically interact with — the single highest-leverage demo feature.

---

## Architecture decisions (already made — do not change without explaining why)

### Tech Stack
| Layer | Technology | Why chosen |
|---|---|---|
| Backend | FastAPI + Uvicorn (Python) | Async, fast, auto-generates /docs, best Python AI library support |
| Agent orchestration | LangGraph | Stateful multi-agent graph, explicit architecture diagram for judges |
| LLM (most agents) | Claude API | Strong structured reasoning, grounded citation-based narrative generation |
| LLM (Compliance Agent only) | Gemini API (`gemini-3.5-flash`) | **Deliberate mid-build deviation** — the project owner explicitly chose Gemini for this one RAG-based narrative-generation call. Every other agent still assumes Claude. Not a full-stack migration; be upfront about this if asked during judging. |
| Time-series DB | TimescaleDB (Postgres extension) | Sensor streams, runs on Postgres so one less system |
| Geospatial | PostGIS + Mapbox or deck.gl | Real geospatial queries, not fake pixel coordinates |
| Knowledge graph | Neo4j | Equipment-permit-risk relationships are graph-shaped (not yet built — see gap below) |
| Vector DB | ChromaDB (local) | Zero external dependency after first run (default embedding model is a one-time local download), fast hackathon setup |
| Streaming | MQTT (simulated IoT) | Simulates real IoT sensor cadence |
| Frontend | React + Tailwind + deck.gl | Fast build, geospatial-native |
| Containerization | Docker + Docker Compose | Start entire stack with one command (backend/simulator/ingest still run manually — see Milestone 10) |

### Multi-Agent Architecture (LangGraph supervisor pattern)
```
Orchestrator (Supervisor Agent) — validates zone, populates shared context
├── Sensor Agent         → wraps the Milestone 4 hybrid rule+ML risk engine [REAL]
├── Permit Agent         → active-permit + sensor-anomaly cross-reference [REAL]
├── Maintenance Agent    → sensor calibration overdue caveat [REAL]
├── Compliance Agent     → RAG over small real regulatory corpus, Gemini-grounded narrative [REAL]
├── Vision Agent         → processes simulated CCTV frames (zone occupancy) [NOT BUILT]
├── Pattern Agent        → queries historical near-miss knowledge graph (needs Neo4j) [NOT BUILT]
└── Risk Synthesis Agent → fuses all outputs → risk score + causal narrative + countdown [REAL]
```
Graph topology: Sensor + Maintenance Agents run in parallel off the Orchestrator;
Permit + Compliance Agents run after Sensor Agent (both consume sensor_result --
the Permit Agent for its permit-x-anomaly co-occurrence scoring, the Compliance
Agent to know what to retrieve); all converge into Risk Synthesis. See
`backend/app/agents/graph.py`. LESSON (found via the causal-chain UI): the Permit
Agent originally ran parallel to the Sensor Agent, so sensor_result was always
empty and the co-occurrence branch NEVER fired (every permit scored 0.1x
baseline). Any agent that reads another agent's output must take its edge from
that agent, not the orchestrator.

**Known gap:** Neo4j / the Pattern Agent's knowledge graph has no assigned milestone yet — worth deciding whether it folds into a future RAG-adjacent milestone or gets its own step.

### Risk scoring approach
**Hybrid: interpretable rules + lightweight ML** (NOT pure black box)
- Rules layer: weighted combination of signal flags from each agent (`backend/app/risk/rules.py`)
- ML layer: GradientBoostingClassifier trained on synthetic labeled compound-risk scenarios (`backend/app/risk/train_model.py`) — honest caveat: 100% test accuracy mostly validates the pipeline, not deep pattern discovery, since the `n_elevated` feature is close to a direct label proxy by construction
- Explainability: every score traces to a `contributing_signals` list the frontend will render as a human-readable causal chain
- Sensor score is the base (rules 60% / ML 40% blend); Permit/Maintenance agents add bonuses on top; Compliance Agent adds explanation only, no numeric bonus (avoids double-counting with Permit Agent)

---

## Folder structure (as of Milestone 6)
```
sentinel/                          (repo root is /Users/bari/Desktop/ETAI)
├── backend/
│   ├── app/
│   │   ├── main.py                FastAPI entry point, all routes
│   │   ├── db.py                  shared psycopg2 connection helper
│   │   ├── simulator/             sensor value simulation + MQTT publisher
│   │   ├── ingest/                MQTT subscriber -> TimescaleDB
│   │   ├── risk/                  hybrid rule+ML risk engine (Milestone 4)
│   │   ├── compliance/            RAG corpus + ChromaDB ingestion (Milestone 6)
│   │   └── agents/                LangGraph nodes + graph assembly (Milestone 5-6)
│   ├── db/init/                   Postgres schema + seed SQL, runs on first container start
│   ├── mqtt/mosquitto.conf
│   └── requirements.txt
├── frontend/                      Vite + React + Tailwind v4 + deck.gl/MapLibre dashboard
│   ├── src/lib/risk.js            shared alarm-color semantics (ISA-101 philosophy)
│   ├── src/components/            StatusBar, ZoneRail, PlantMap, ZoneDetailPanel
│   └── scripts/screenshot.mjs     Playwright headless verification (screenshot + click)
├── docker-compose.yml             db (TimescaleDB+PostGIS) + mqtt (Mosquitto)
├── .env / .env.example
├── .gitignore
├── README.md                      setup/run instructions, kept in sync with reality
└── CLAUDE_CONTEXT.md              this file
```

---

## Milestones — progress tracker

| # | Milestone | Status |
|---|---|---|
| 0 | Foundations — concepts, no code | ✅ Done |
| 1 | Project setup, hello world backend + frontend | ✅ Done |
| 2 | Database (TimescaleDB + PostGIS + Docker) | ✅ Done |
| 3 | Simulated IoT sensor data generator | ✅ Done |
| 4 | Core Risk Engine (hybrid rule+ML scorer) | ✅ Done |
| 5 | Multi-agent system (LangGraph) — Orchestrator, Sensor, Permit, Maintenance, Risk Synthesis | ✅ Done |
| 6 | RAG over safety regulations — Compliance Agent (Gemini + ChromaDB) | ✅ Done |
| 7 | Geospatial map (digital twin plant view) | ✅ Done |
| 8 | Frontend screens (design system + dashboard) | ✅ Done |
| 9 | What-If slider (wow-factor demo feature) | ✅ Done |
| 10 | Polish, deployment, demo rehearsal | ✅ Done |

---

## Current stopping point
Milestones 7-8 just completed. The dashboard is live at localhost:5173: dark
control-room design (tokens in `frontend/src/index.css`; ISA-101 philosophy — color
only for abnormality), zone annunciator rail, deck.gl plant map over a free CARTO
dark basemap, and a detail panel that runs the full multi-agent assessment
(including the Gemini compliance narrative and a live time-to-critical countdown).

**Hard-won lessons — do not relearn these:**
- Project Postgres is on port 55432, NOT 5432: a native macOS Postgres auto-starts
  on boot and squats localhost:5432 — connections silently reach it instead of the
  container ("role sentinel does not exist"). Port set via POSTGRES_PORT in .env.
- Free-tier Gemini quota is ~20 requests/day PER MODEL. The compliance agent
  therefore: caches narratives 10 min per situation, never retries 429s, falls back
  to gemini-3.1-flash-lite (separate quota), then degrades gracefully (citations
  still shown). A missing GEMINI_API_KEY disables narrative, never blocks startup.
- Backend has a pytest suite (backend/tests/, `python -m pytest tests/` from the
  venv; deps in requirements-dev.txt). Run it after touching app/risk or the API.
- Alarm MEDIUM color is #facc15 (not Tailwind's default amber #eab308) — validated
  for deuteranopia separation from HIGH's orange via the dataviz skill's validator.
- Synthetic training data blind spot (found via the what-if simulator): the spike
  generator only produced RISING anomalies, so the ML model learned "dangerous means
  rising" and scored steady-state elevation ~0%. Fixed in train_model.py
  (`_spiked_signal` now mixes rising + plateaued, z range 2.5-15) — if you regenerate
  training data, keep that mixture. Retrain with `python -m app.risk.train_model`,
  then RESTART the backend (the model loads at import).
- Live scoring and what-if simulation share ONE code path: `engine.score_signals`.
  Never fork a lookalike scoring implementation for simulations.
- react-map-gl v8 + deck.gl v9: `Map` must be the parent with a `MapboxOverlay`
  attached via `useControl` (works for MapLibre). The old `<DeckGL><Map/></DeckGL>`
  child pattern renders a blank basemap with NO console errors.
- UI claims require picture proof: use `frontend/scripts/screenshot.mjs` (Playwright)
  to screenshot/click before declaring frontend work done. A Playwright MCP server is
  registered in `.mcp.json` (approve it when prompted in a new session).
- Seeded permits expire ~4h after volume creation (relative timestamps). Re-arm
  before demos: see "Demo freshness" in README. A proper demo-reset script belongs
  in Milestone 10.
- The official `frontend-design` skill is installed at `.claude/skills/frontend-design/`
  — apply its two-pass process (token plan → critique → build → screenshot critique)
  to all new UI work.

**Demo-hardening phase (post-Milestone-9, pre-10) — completed items:**
- Executive briefing screen (`frontend/src/components/BriefingScreen.jsx`,
  Operations|Briefing tabs in StatusBar, `?view=briefing` deep link). HARD RULE:
  every statistic on it comes from the user's approved-facts list; gaps carry a
  literal [NEEDS VERIFICATION: ...] placeholder — never fill one with a guess.
  Two placeholders currently await user-supplied sources (Vizag year, factory-
  count attribution).
- Scripted demo scenarios: `POST /demo/scenario` (app/demo.py) publishes a
  RETAINED MQTT control message on `sentinel/control/scenario`; the simulator
  subscribes, ramps targeted sensors toward z=15σ offsets (ASYMMETRIC ramp:
  7%/tick up so the ticking time-to-critical countdown stays visible ~20s
  before z crosses 6, 30%/tick down so reset clears fast — at 20%/tick up the
  countdown window was only ~6s and judges would never see it), suppresses
  random spikes plant-wide during a scripted scenario (a chance co-spike in an
  untargeted zone once hit CRITICAL 86.8 mid-verification — that's why), and
  clears in-flight spikes on any transition. Frontend controls at the bottom of
  the zone rail (DemoControls.jsx). Tests in backend/tests/test_demo.py mock
  `demo._publish_control` so the suite needs no broker. The publisher process
  must be RESTARTED after simulator code changes — it doesn't hot-reload.

All five demo-hardening tasks are done (briefing screen, scripted scenarios,
what-if count-up + COMPOUND banner, dramatized countdown, source-typed causal
chain), plus the permit-agent topology fix.

**Milestone 10 (done):** one-command stack — `docker compose up -d --build`
runs db, mqtt, api, simulator, ingest (backend/Dockerfile builds one image,
three commands; ML model + ChromaDB index baked at BUILD time so the venue
needs no internet). `scripts/demo_reset.sh` = calm scenario + permit re-arm +
sanity check. DEMO.md = the rehearsed 4-minute script with recovery moves.
Dev workflow unchanged: `up -d db mqtt` + local uvicorn --reload still works,
but never run the api container and local uvicorn together (both bind :8000).

**Briefing facts (resolved 2026-07-04):** Vizag Steel Plant ladle explosion
= 8 June 2025 (8 killed, entrapped gases). Inspection-gap / factory-count
figures attributed to "DGFASLI data, as reported in NCRB/FACTLY analysis."
No [NEEDS VERIFICATION] placeholders remain in any user-visible screen.

**Remaining before submission:** rehearse DEMO.md live at least once.

---

## Mentor rules (always follow these)
1. Teach every new technology before using it
2. Explain what every file does and what every significant code block does
3. Write production-quality, enterprise-level code
4. For every technology: explain what it is, why we chose it, why alternatives were rejected
5. At end of each milestone, stop and confirm understanding before moving forward
6. **Sonnet is enough** for almost everything. Flag explicitly when Opus is needed (complex multi-agent logic design, hard debugging).
7. Never skip steps. Never leave gaps.
8. Optimize every decision for winning the hackathon, not just completing the project.
