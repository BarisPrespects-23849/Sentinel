"""Orchestrator (Supervisor Agent): validates the target zone and
populates shared context before fanning work out to the specialist
agents. Runs once per assessment rather than duplicating this lookup
in every downstream node.
"""

from app.agents.state import AgentState


def make_orchestrator(conn):
    def orchestrator(state: AgentState) -> dict:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM zones WHERE zone_id = %s", (state["zone_id"],))
            row = cur.fetchone()
        if row is None:
            raise ValueError(f"Zone {state['zone_id']} not found")
        return {"zone_name": row[0]}

    return orchestrator
