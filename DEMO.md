# SENTINEL — Demo Runbook

A rehearsed, deterministic 4-minute demo. Nothing in it depends on random
sensor noise; every dramatic beat is triggered on cue.

## Pre-flight (do this ~10 minutes before)

```bash
docker compose up -d --build      # full stack: db, mqtt, api, simulator, ingest
cd frontend && npm run dev &      # dashboard on http://localhost:5173
./scripts/demo_reset.sh           # calm state + fresh permits + API sanity check
```

Checklist:

- [ ] **Close all non-essential host apps first.** The daemon crashes are
      host-side memory pressure on an 8 GB machine — quit spare browser
      windows/tabs, and if possible VS Code and other memory-heavy apps.
      Leave only the demo browser (and terminal) running. This is the single
      highest-impact thing you can do to prevent a mid-demo crash.
- [ ] **`docker info` responds and `docker ps` shows 5 healthy containers**
      (db, mqtt, api, simulator, ingest). If the daemon isn't responding,
      restart Docker Desktop **now, before the session** — never mid-demo.
- [ ] `./scripts/demo_reset.sh` printed `== ready to demo ==`
- [ ] Dashboard shows all three zones LOW/steel (wait ~60s after reset)
- [ ] Click a zone once: assessment loads, regulation card shows a cited
      narrative (if it says "narrative unavailable (LLM daily quota
      exhausted)", the demo still works — the citations remain; mention
      the graceful degradation as a feature, because it is one)
- [ ] Close the zone panel again
- [ ] If Wi-Fi is down: everything works offline except the CARTO basemap
      tiles and the Gemini narrative — both degrade, nothing breaks

## The script (≈4 minutes)

**Beat 1 — the thesis (30s).** Open the **Briefing** tab. Point at the
chart: *"India's hazardous-process factories grew 69% since 2010, while
inspection coverage collapsed from 62% to 39%. Nobody is watching most of
these plants most of the time. SENTINEL is the always-on intelligence
layer for the gap."* Switch to **Operations**.

**Beat 2 — the calm plant (20s).** *"Live digital twin: three zones, seven
sensors streaming over MQTT into a time-series database. Everything is
normal — and notice the screen is almost colorless. In a control room,
color is reserved for danger."*

**Beat 3 — the incident (60s).** Select **Compressor House**, then press
**Inject compound** (bottom-left panel). *"We're simulating a gas leak
near hot work — the exact pattern that killed nine workers at Bhilai in
2018."* Narrate what appears, in order:

1. Sensor readings climb on the map tooltip / zone rail
2. **Time-to-critical countdown** appears and ticks down, shifting color
3. Score crosses into HIGH, then CRITICAL; zone floods red
4. Re-select the zone: the **causal chain** now leads with the red
   COMPOUND RISK card — *"two sensor types elevated at once"*
5. Point at the **work permit card**: *"+25 — SENTINEL knows welding is
   authorized in this zone right now, and that this combination is what
   turns an anomaly into an emergency"*
6. Point at the **regulation card**: *"and it cites the actual regulation
   — retrieved from a real corpus, generated grounded, nothing invented"*

**Beat 4 — the judges drive (60s).** Open the **what-if sliders**:
*"Ask me any scenario."* Drag gas up alone → score stays modest, ML near
zero. *"A single anomaly is just a Tuesday."* Add temperature → count-up
animation, **COMPOUND RISK DETECTED** banner flashes, 2.0× multiplier.
*"THIS is the detection that doesn't exist in siloed systems — and it's
scored by the same engine as the live data, not a mock."*

**Beat 5 — reset + close (30s).** Press **Reset to calm**. *"Scores settle
in seconds. Under the hood: seven agents in a LangGraph, a hybrid
rules-plus-ML scorer where every point is traceable, TimescaleDB +
PostGIS, RAG over real regulations. One `docker compose up` runs all of
it."*

## Recovery moves

| Symptom | Move |
|---|---|
| API 503 / all zones unreachable / "link down" mid-demo. **Likely cause: Docker daemon crashed (host memory pressure on this 8 GB machine).** | **Step 0 (if `docker info` fails — the usual case):** relaunch Docker Desktop and wait for the whale icon to settle, ~30–60s. **Then:** `docker compose up -d --build` (~15s to healthy) → `./scripts/demo_reset.sh` (~2s) → confirm 5 healthy containers with `docker ps`. **Total ~45–75s** (dominated by the Docker Desktop relaunch, not the stack). |
| Zone stuck elevated | `./scripts/demo_reset.sh`, wait 15s |
| "link down" in status bar | `docker compose restart api`, refresh browser |
| Regulation card degraded (quota) | Say: "LLM quota exhausted — note the system degraded gracefully instead of failing; citations still shown" |
| Basemap tiles missing (no Wi-Fi) | Zones/sensors still render on dark canvas; proceed |
| Everything on fire | `docker compose down && docker compose up -d`, `./scripts/demo_reset.sh` (~90s) |

## Talking points if asked

- **"Is the ML real?"** GradientBoosting on synthetic compound scenarios;
  honest caveat baked into the docs — it validates the pipeline. Rules
  carry 60% of the weight *by design*: a safety system should not be a
  black box. Every score decomposes into the cards on screen.
- **"Would this have prevented Bhilai?"** Careful, honest answer: *"We
  don't claim that. We claim it detects the documented pattern — hazardous
  permitted work coinciding with a gas anomaly — which is what the record
  shows happened there."*
- **"What's fake?"** Sensors are simulated (random walk + scripted
  scenarios over real MQTT); permits/maintenance are seeded; the
  regulation corpus is small but real and cited. The pipeline —
  MQTT → TimescaleDB → agents → fusion — is the real architecture.
