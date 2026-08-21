"""WebSocket bridge connecting Python Mitchell core to the Electron Orb UI."""

import asyncio
import json
from typing import Any, Callable, Dict, Optional, Set
from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.manager.loop import Manager

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WEBSOCKETS_AVAILABLE = False


class OrbBridgeServer:
    """WebSocket server providing real-time state and message synchronization with Electron Orb."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        manager: Optional[Manager] = None,
    ) -> None:
        self.host = host or settings.orb_host
        self.port = port or settings.orb_port
        self.manager = manager or Manager()
        self.clients: Set[Any] = set()
        self.current_status: str = "idle"  # idle | thinking | working | needs_attention | error
        self.server = None

    async def start(self) -> None:
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets library not installed. Orb bridge server disabled.")
            return

        logger.info("Starting Orb Bridge WebSocket server on ws://{}:{}", self.host, self.port)
        self.server = await websockets.serve(self._handle_client, self.host, self.port)

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Orb Bridge server stopped.")

    async def _handle_client(self, websocket: Any) -> None:
        """Handle incoming WebSocket connection from Electron Orb."""
        self.clients.add(websocket)
        logger.info("Electron Orb connected from {}", websocket.remote_address)

        # Send initial state
        await websocket.send(
            json.dumps({
                "type": "state",
                "status": self.current_status,
                "history": [msg.model_dump() for msg in self.manager.get_history()],
            })
        )

        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                    msg_type = data.get("type", "message")

                    if msg_type == "message":
                        user_text = data.get("content", "")
                        if user_text:
                            # Update status to thinking/working
                            await self.set_status("thinking")

                            # Process through Manager
                            response = self.manager.receive(user_text)

                            # Send response back to Orb
                            await self.broadcast({
                                "type": "response",
                                "content": response,
                                "status": "idle",
                            })
                            await self.set_status("idle")

                    elif msg_type == "get_status":
                        await websocket.send(json.dumps({"type": "status", "status": self.current_status}))

                    elif msg_type == "get_events":
                        recent = event_log.get_recent(10)
                        await websocket.send(
                            json.dumps({
                                "type": "events",
                                "events": [
                                    {
                                        "id": e.id,
                                        "type": e.type,
                                        "source": e.source,
                                        "data": e.data,
                                        "timestamp": e.timestamp.isoformat(),
                                    }
                                    for e in recent
                                ],
                            })
                        )

                except Exception as err:
                    logger.error("Error processing Orb message: {}", err)
                    await websocket.send(json.dumps({"type": "error", "message": str(err)}))

        except Exception as e:
            logger.debug("Orb client disconnected: {}", e)
        finally:
            self.clients.remove(websocket)

    async def set_status(self, status: str) -> None:
        """Update system status and notify all connected Orb clients."""
        self.current_status = status
        await self.broadcast({"type": "status", "status": status})

    async def broadcast(self, message_dict: Dict[str, Any]) -> None:
        """Broadcast payload to all connected Electron Orbs."""
        if not self.clients:
            return
        payload = json.dumps(message_dict)
        await asyncio.gather(
            *[client.send(payload) for client in self.clients],
            return_exceptions=True,
        )


orb_bridge = OrbBridgeServer()

__all__ = ["OrbBridgeServer", "orb_bridge", "WEBSOCKETS_AVAILABLE"]
