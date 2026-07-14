"""Maintenance Agent: checks sensor calibration status.

An overdue-calibration sensor's readings are less trustworthy, which is
a caveat on the explanation more than a risk driver in its own right --
so this contributes a small flat bonus (not scaled by how many sensors
are overdue) and, more importantly, surfaces the caveat in
contributing_signals so a human reviewing an alert knows to weigh that
sensor's reading with appropriate skepticism.
"""

from app.agents.state import AgentState

OVERDUE_BONUS = 5


def make_maintenance_agent(conn):
    def maintenance_agent(state: AgentState) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT mr.sensor_id, mr.next_due
                FROM maintenance_records mr
                JOIN sensors s ON s.sensor_id = mr.sensor_id
                WHERE s.zone_id = %s AND mr.next_due < now()
                """,
                (state["zone_id"],),
            )
            overdue = cur.fetchall()

        signals = [
            {
                "source": "maintenance",
                "sensor_id": sensor_id,
                "sensor_type": None,
                "description": (
                    f"Sensor {sensor_id} is overdue for calibration (was due {next_due:%Y-%m-%d}) "
                    f"-- treat its readings with reduced confidence"
                ),
                "weight_contribution": 0,
            }
            for sensor_id, next_due in overdue
        ]
        bonus = OVERDUE_BONUS if overdue else 0

        return {"maintenance_result": {"bonus": bonus, "signals": signals}}

    return maintenance_agent
