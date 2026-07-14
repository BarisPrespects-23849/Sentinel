"""Risk Synthesis Agent: fuses every specialist agent's output into one
final score, level, and causal-chain explanation.

The sensor-based hybrid score (rules + ML, from Milestone 4) is the base
-- it's the primary, always-available risk driver. Permit and
maintenance agents contribute additive bonuses/caveats on top, each
fully traceable in contributing_signals. The Compliance Agent contributes
a citation-grounded explanation, not a numeric bonus -- it answers WHY a
situation is regulation-relevant, which would double-count with the
Permit Agent's scoring if it also moved the number. Vision and Pattern
agents will plug into this same fusion step once they have real data
sources (see app/agents/graph.py for where they'll attach).
"""

from app.risk.engine import risk_level as compute_risk_level
from app.agents.state import AgentState


def risk_synthesis_agent(state: AgentState) -> dict:
    sensor = state.get("sensor_result") or {}
    permit = state.get("permit_result") or {"bonus": 0, "signals": []}
    maintenance = state.get("maintenance_result") or {"bonus": 0, "signals": []}
    compliance = state.get("compliance_result") or {"signals": []}

    base_score = sensor.get("risk_score") or 0
    final_score = min(100.0, base_score + permit["bonus"] + maintenance["bonus"])

    contributing_signals = (
        list(sensor.get("contributing_signals") or [])
        + permit["signals"]
        + maintenance["signals"]
        + compliance["signals"]
    )

    return {
        "final_result": {
            "zone_id": state["zone_id"],
            "zone_name": state["zone_name"],
            "risk_score": round(final_score, 1),
            "risk_level": compute_risk_level(final_score),
            "sensor_score": sensor.get("risk_score"),
            "permit_bonus": round(permit["bonus"], 1),
            "maintenance_bonus": maintenance["bonus"],
            "time_to_critical_seconds": sensor.get("time_to_critical_seconds"),
            # Pass the single-sensor baseline through untouched -- it's a
            # property of the raw sensor readings, unaffected by permit /
            # maintenance fusion, so the sensor agent's value is final.
            "single_sensor_baseline": sensor.get("single_sensor_baseline"),
            "contributing_signals": contributing_signals,
        }
    }
