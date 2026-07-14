"""Shared state schema passed between every node in the SENTINEL graph.

Each agent node writes to its OWN key only (sensor_result, permit_result,
maintenance_result). That's deliberate: LangGraph merges partial state
updates from parallel branches key-by-key, so as long as no two nodes
write the same key, there's no merge conflict to resolve and no custom
reducer function is needed.
"""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    zone_id: int
    zone_name: str
    sensor_result: dict
    permit_result: dict
    maintenance_result: dict
    compliance_result: dict
    final_result: dict
