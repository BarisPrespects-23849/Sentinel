"""Assembles the SENTINEL LangGraph:

                        +--> maintenance_agent ----------------+
    START -> orchestrator                                      +--> risk_synthesis -> END
                        +--> sensor_agent --> permit_agent ----+
                                        \\--> compliance_agent-+

maintenance_agent depends only on the orchestrator's output
(zone_id/zone_name), so LangGraph runs it concurrently with sensor_agent
as one "superstep." permit_agent and compliance_agent are different: both
need the sensor_agent's output (permit_agent checks whether a hazardous
permit CO-OCCURS with elevated readings -- its whole scoring branch; the
compliance_agent needs the elevated sensor types to decide what to
retrieve), so they hang off sensor_agent and run one step later, in
parallel with each other. risk_synthesis has edges from all three leaf
nodes and only runs once every one of them has completed.

HISTORY: permit_agent originally fanned out from the orchestrator in
parallel with sensor_agent -- which meant state["sensor_result"] was
always empty when it looked, and the co-occurrence check silently never
fired (every permit scored the 0.1x baseline). Found when the causal-chain
UI showed "no elevated sensor readings" beside a 10.7 sigma sensor card.
If you add an agent that reads another agent's output, its edge must come
FROM that agent, not from the orchestrator.

NOT YET WIRED (planned, not stubbed -- see README): Vision Agent (needs
simulated CCTV data), Pattern Agent (needs the Neo4j knowledge graph, not
yet built). Each would add one more node following the same pattern.
"""

from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.agents.orchestrator import make_orchestrator
from app.agents.sensor_agent import make_sensor_agent
from app.agents.permit_agent import make_permit_agent
from app.agents.maintenance_agent import make_maintenance_agent
from app.agents.compliance_agent import make_compliance_agent
from app.agents.risk_synthesis_agent import risk_synthesis_agent


def build_graph(conn):
    g = StateGraph(AgentState)

    g.add_node("orchestrator", make_orchestrator(conn))
    g.add_node("sensor_agent", make_sensor_agent(conn))
    g.add_node("permit_agent", make_permit_agent(conn))
    g.add_node("maintenance_agent", make_maintenance_agent(conn))
    g.add_node("compliance_agent", make_compliance_agent(conn))
    g.add_node("risk_synthesis", risk_synthesis_agent)

    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "sensor_agent")
    g.add_edge("orchestrator", "maintenance_agent")
    # permit_agent reads sensor_result for its co-occurrence check, so it
    # must run AFTER sensor_agent -- see HISTORY note in the module docstring.
    g.add_edge("sensor_agent", "permit_agent")
    g.add_edge("sensor_agent", "compliance_agent")
    g.add_edge("compliance_agent", "risk_synthesis")
    g.add_edge("permit_agent", "risk_synthesis")
    g.add_edge("maintenance_agent", "risk_synthesis")
    g.add_edge("risk_synthesis", END)

    return g.compile()


def assess_zone(conn, zone_id: int) -> dict:
    graph = build_graph(conn)
    result = graph.invoke({"zone_id": zone_id})
    return result["final_result"]
