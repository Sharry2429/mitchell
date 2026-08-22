"""Lightweight HTTP server providing live workflow state and blackboard streaming."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from mitchell.core.cost import cost_tracker
from mitchell.core.event_log import event_log
from mitchell.hive.blackboard import blackboard
from mitchell.core.logging import logger


class StudioStateProvider:
    """Aggregates live state across blackboard, costs, and event log for the studio."""

    def get_full_state(self) -> Dict[str, Any]:
        """Aggregate current snapshot of the Mitchell hive state."""
        return {
            "blackboard": blackboard.dump_state(),
            "cost": cost_tracker.get_summary(),
            "recent_events": [e.model_dump() for e in event_log.get_recent(n=25)],
        }


studio_state = StudioStateProvider()


class StudioHTTPHandler(BaseHTTPRequestHandler):
    """Handles studio web requests and JSON API state endpoints."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default console logging for cleaner terminal output."""
        pass

    def do_GET(self) -> None:
        """Serve studio dashboard and live API state."""
        if self.path in ("/", "/studio", "/index.html"):
            docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
            studio_file = docs_dir / "studio.html"
            if studio_file.exists():
                content = studio_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if self.path.startswith("/api/state"):
            data = json.dumps(studio_state.get_full_state()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")


class MitchellStudioServer:
    """Standalone server hosting the Mitchell Workflow Studio."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8500) -> None:
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None

    def start(self) -> None:
        """Start the studio HTTP server."""
        self.server = HTTPServer((self.host, self.port), StudioHTTPHandler)
        logger.info("Mitchell Studio Server running at http://{}:{}", self.host, self.port)
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            if self.server:
                self.server.server_close()
                logger.info("Mitchell Studio Server stopped.")


__all__ = ["MitchellStudioServer", "studio_state"]
