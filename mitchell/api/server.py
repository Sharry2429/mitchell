"""Unified asynchronous REST API and Webhook server for Mitchell."""

import asyncio
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any, Dict, Optional

from mitchell.core.cost import cost_tracker
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.core.watchdog import watchdog
from mitchell.manager import Manager
from mitchell.skills.library import skill_library
from mitchell.tools.registry import tool_registry

manager_instance = Manager()


class MitchellHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler providing REST endpoints for Mitchell."""

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Send JSON response with CORS headers."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET endpoints."""
        path = self.path.split("?")[0]

        if path in ("/", "/health"):
            health = watchdog.run_health_check()
            self._send_json(health)
            return

        if path == "/api/v1/tools":
            tools = tool_registry.list_tools()
            self._send_json({"tools": tools, "count": len(tools)})
            return

        if path == "/api/v1/skills":
            skills = [s.model_dump(mode="json") for s in skill_library.list_skills()]
            self._send_json({"skills": skills, "count": len(skills)})
            return

        if path == "/api/v1/cost":
            cost = cost_tracker.get_summary()
            self._send_json(cost)
            return

        if path == "/api/v1/events":
            events = [
                {
                    "timestamp": ev.timestamp.isoformat(),
                    "type": ev.type,
                    "source": ev.source,
                    "data": ev.data,
                }
                for ev in event_log.get_recent(20)
            ]
            self._send_json({"events": events, "count": len(events)})
            return

        self._send_json({"error": "Endpoint not found", "path": path}, status=404)

    def do_POST(self) -> None:
        """Handle POST endpoints."""
        path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)

        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            payload = {}

        if path == "/api/v1/goal":
            goal = payload.get("goal") or payload.get("prompt", "")
            if not goal:
                self._send_json({"error": "Missing 'goal' field in request body"}, status=400)
                return

            response = manager_instance.receive(goal)
            self._send_json({
                "goal": goal,
                "response": response,
                "status": "success",
            })
            return

        if path == "/api/v1/webhook":
            event_type = payload.get("event", "incoming_webhook")
            event_log.log_event("webhook_received", source="api_server", data=payload)
            self._send_json({"status": "received", "event": event_type})
            return

        self._send_json({"error": "Endpoint not found", "path": path}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        """Redirect internal HTTP logs to Mitchell logger."""
        logger.debug("API: " + format, *args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server for non-blocking concurrent API handling."""

    daemon_threads = True


class MitchellAPIServer:
    """REST API Server management."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self.server: Optional[ThreadedHTTPServer] = None

    def start(self) -> None:
        """Start the HTTP server."""
        self.server = ThreadedHTTPServer((self.host, self.port), MitchellHTTPRequestHandler)
        logger.info("Mitchell REST API Server running at http://{}:{}", self.host, self.port)
        self.server.serve_forever()

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()


api_server = MitchellAPIServer()

__all__ = ["MitchellAPIServer", "api_server", "MitchellHTTPRequestHandler"]
