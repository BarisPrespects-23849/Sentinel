"""Sensor Agent: reads gas/temp/pressure trends, detects rate-of-change
anomalies.

This is intentionally a thin wrapper -- the actual signal extraction,
rule scoring, and ML scoring were already built and verified in
Milestone 4 (app.risk.engine). Wrapping proven logic in a graph node,
rather than reimplementing it, is the point: LangGraph orchestrates
*existing* capabilities, it doesn't replace them.
"""

from app.risk import engine
from app.agents.state import AgentState


def make_sensor_agent(conn):
    def sensor_agent(state: AgentState) -> dict:
        result = engine.score_zone(conn, state["zone_id"], state["zone_name"])
        return {"sensor_result": result}

    return sensor_agent
