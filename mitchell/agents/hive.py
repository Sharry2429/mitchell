"""
mitchell.agents.hive
====================
The central coordination substrate (Mailbox, Blackboard, Event Log).
"""

import os
import json
import time
import asyncio
from pathlib import Path

class HiveSubstrate:
    def __init__(self, base_dir: str = "~/.mitchell_hive"):
        self.base_dir = Path(os.path.expanduser(base_dir))
        self.inbox_dir = self.base_dir / "inbox"
        self.outbox_dir = self.base_dir / "outbox"
        self.blackboard_file = self.base_dir / "blackboard.json"
        self.event_log_file = self.base_dir / "events.jsonl"
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        if not self.blackboard_file.exists():
            self.blackboard_file.write_text("{}")
        if not self.event_log_file.exists():
            self.event_log_file.touch()

    def write_event(self, source: str, event_type: str, data: dict):
        event = {
            "timestamp": time.time(),
            "source": source,
            "type": event_type,
            "data": data
        }
        with open(self.event_log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def read_blackboard(self) -> dict:
        try:
            return json.loads(self.blackboard_file.read_text())
        except Exception:
            return {}

    def update_blackboard(self, key: str, value: any):
        board = self.read_blackboard()
        board[key] = value
        self.blackboard_file.write_text(json.dumps(board, indent=2))

    def send_message(self, sender: str, recipient: str, content: str):
        msg_id = str(int(time.time() * 1000))
        msg = {
            "id": msg_id,
            "sender": sender,
            "recipient": recipient,
            "content": content,
            "timestamp": time.time()
        }
        # Direct delivery to recipient inbox for simplicity in v1
        recipient_dir = self.inbox_dir / recipient
        recipient_dir.mkdir(exist_ok=True)
        (recipient_dir / f"{msg_id}.json").write_text(json.dumps(msg))
        self.write_event(sender, "message_sent", {"recipient": recipient, "id": msg_id})

    def get_messages(self, recipient: str) -> list[dict]:
        recipient_dir = self.inbox_dir / recipient
        if not recipient_dir.exists():
            return []
            
        msgs = []
        for file_path in recipient_dir.glob("*.json"):
            try:
                msgs.append(json.loads(file_path.read_text()))
                file_path.unlink() # Delete after reading
            except Exception:
                pass
        return sorted(msgs, key=lambda x: x.get("timestamp", 0))

_global_hive = None

def get_hive() -> HiveSubstrate:
    global _global_hive
    if not _global_hive:
        _global_hive = HiveSubstrate()
    return _global_hive
