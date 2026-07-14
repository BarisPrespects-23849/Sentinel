"""Permit Agent: monitors active work permits and flags when a hazardous
permit overlaps with elevated sensor readings in the same zone.

A permit being active is not, by itself, dangerous -- a hot-work permit
during calm sensor readings is routine. It becomes a compound risk
specifically when it coincides with an active sensor anomaly (e.g.
welding sparks + a gas leak). That co-occurrence check is the entire
point of this agent; it's a second, independent axis of "compound risk"
beyond sensor-to-sensor combinations.
"""

from app.agents.state import AgentState

# Maximum points this permit type can contribute when it overlaps an
# active sensor anomaly. Illustrative severity ranking, not sourced from
# a real regulatory schedule (see rules.py for the same caveat).
PERMIT_TYPE_WEIGHT = {"hot_work": 25, "confined_space": 15, "cold_work": 5}

# Small informational contribution even with no co-occurring anomaly --
# "a hazardous permit is open here" is still worth surfacing, just not
# worth much risk weight on its own.
BASELINE_FACTOR = 0.1

MAX_BONUS = 25


def make_permit_agent(conn):
    def permit_agent(state: AgentState) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT permit_type, description
                FROM permits
                WHERE zone_id = %s AND status = 'active'
                  AND now() BETWEEN valid_from AND valid_until
                """,
                (state["zone_id"],),
            )
            active_permits = cur.fetchall()

        sensor_result = state.get("sensor_result") or {}
        sensor_elevated = (sensor_result.get("rule_score") or 0) > 0

        signals = []
        bonus = 0.0
        for permit_type, description in active_permits:
            weight = PERMIT_TYPE_WEIGHT.get(permit_type, 5)
            if sensor_elevated:
                contribution = weight
                note = "sensors in this zone are currently elevated -- ignition/exposure risk compounds"
            else:
                contribution = weight * BASELINE_FACTOR
                note = "no elevated sensor readings right now"
            bonus += contribution
            signals.append({
                "source": "permit",
                "sensor_id": None,
                "sensor_type": None,
                "description": (
                    f"Active {permit_type} permit in this zone ({description}) -- {note}"
                ),
                "weight_contribution": round(contribution, 1),
            })

        return {"permit_result": {"bonus": min(bonus, MAX_BONUS), "signals": signals}}

    return permit_agent
