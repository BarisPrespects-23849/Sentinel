#!/usr/bin/env bash
# Resets SENTINEL to a demo-ready state:
#   1. Commands the simulator back to calm (clears any scripted scenario)
#   2. Re-arms the seeded permits (they carry relative timestamps and
#      expire ~4h after the database volume is created)
#   3. Optionally clears historical sensor readings (--clear-readings)
#
# Usage:  ./scripts/demo_reset.sh [--clear-readings]
#
# Requires the stack to be running (docker compose up -d) and the API on
# localhost:8000.

set -euo pipefail

API=${API:-http://localhost:8000}
DB_CONTAINER=${DB_CONTAINER:-sentinel-db}

fail() { echo "ERROR: $1" >&2; exit 1; }

echo "== SENTINEL demo reset =="

# 1. Calm scenario -- do this first so readings decay while we re-arm.
if curl -sf -X POST "$API/demo/scenario" \
     -H "Content-Type: application/json" \
     -d '{"scenario": "calm"}' > /dev/null; then
  echo "ok: calm scenario sent (scores settle in ~15s)"
else
  fail "could not reach the API at $API -- is the stack up?"
fi

# 2. Re-arm every seeded permit with a fresh validity window.
docker exec "$DB_CONTAINER" psql -q -U "${POSTGRES_USER:-sentinel}" \
  -d "${POSTGRES_DB:-sentinel}" -c "
  UPDATE permits
  SET valid_from = now() - interval '2 hours',
      valid_until = now() + interval '4 hours'
  WHERE status = 'active';" \
  || fail "permit re-arm failed -- is the $DB_CONTAINER container running?"
echo "ok: permits re-armed (valid for the next 4 hours)"

# 3. Optional: wipe reading history so charts/scores start from a blank
#    slate. NOT done by default -- a populated last-hour looks more real.
if [[ "${1:-}" == "--clear-readings" ]]; then
  docker exec "$DB_CONTAINER" psql -q -U "${POSTGRES_USER:-sentinel}" \
    -d "${POSTGRES_DB:-sentinel}" -c "TRUNCATE sensor_readings;"
  echo "ok: sensor_readings cleared"
fi

# 4. Sanity check: the plant endpoint answers and all zones exist.
zones=$(curl -sf "$API/geo/plant" | python3 -c \
  "import json,sys; print(len(json.load(sys.stdin)['zones']['features']))")
echo "ok: API healthy, $zones zones live"
echo "== ready to demo =="
