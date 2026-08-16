"""
mitchell.agents.hive_client
===========================
Thin client for agents to interact with the hive.
"""

from mitchell.agents.hive import get_hive

class HiveClient:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.hive = get_hive()

    def check_messages(self) -> list[dict]:
        """Check the inbox for new messages."""
        return self.hive.get_messages(self.agent_id)

    def send_message(self, recipient: str, content: str):
        """Send a message to another agent or orchestrator."""
        self.hive.send_message(self.agent_id, recipient, content)

    def report_status(self, status: str, details: dict | None = None):
        """Write a status update to the event log."""
        self.hive.write_event(self.agent_id, "status_update", {"status": status, "details": details or {}})

    def complete_task(self, result: str):
        """Mark task as completed."""
        self.report_status("completed", {"result": result})

    def fail_task(self, error: str):
        """Mark task as failed."""
        self.report_status("failed", {"error": error})

    def write_blackboard(self, key: str, value: any):
        """Update shared blackboard state."""
        self.hive.update_blackboard(key, value)

    def read_blackboard(self) -> dict:
        """Read shared blackboard state."""
        return self.hive.read_blackboard()
