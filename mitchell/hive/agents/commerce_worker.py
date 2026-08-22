"""Commerce Worker Agent executing product search, price tracking, and deal discovery."""

import json
from typing import Any, Dict, Union

from mitchell.commerce import commerce_assistant, commerce_search, price_tracker
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent


class CommerceWorkerAgent(BaseAgent):
    """Hive Agent specializing in marketplace search, price tracking, and coupon discovery."""

    def __init__(
        self,
        agent_id: str = "commerce_worker",
        description: str = "Searches products across marketplaces, tracks price drops, and finds coupons",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process commerce task."""
        logger.info("CommerceWorker received task from {}: {}", sender, message)

        if isinstance(message, dict):
            action = message.get("action", "")
            data = message
        else:
            text = str(message).strip()
            parts = text.split(maxsplit=1)
            action = parts[0].lower() if parts else ""
            data = {"raw": parts[1]} if len(parts) > 1 else {}

        event_log.log_event(
            "commerce_worker_task_started",
            source=self.agent_id,
            data={"action": action, "sender": sender},
        )

        try:
            if action in ("search", "find_product"):
                query = data.get("query") or data.get("raw") or ""
                results = commerce_search.search_product(query=query)
                return {"status": "success", "results": [r.model_dump(mode="json") for r in results]}

            elif action in ("track", "track_price"):
                title = data.get("title") or data.get("raw") or "Product"
                current = float(data.get("current_price", 1000))
                target = float(data.get("target_price", 900))
                url = data.get("url", "")
                item = price_tracker.track_product(title=title, current_price=current, target_price=target, url=url)
                return {"status": "success", "tracked_item": item.model_dump(mode="json")}

            elif action in ("coupons", "deals"):
                store = data.get("store") or data.get("raw") or "Amazon"
                coupons = commerce_assistant.find_coupons(store_name=store)
                return {"status": "success", "coupons": [c.model_dump(mode="json") for c in coupons]}

            return {"status": "success", "message": f"Commerce task processed: {message}"}

        except Exception as e:
            logger.error("CommerceWorker error: {}", e)
            return {"status": "error", "error": str(e)}


__all__ = ["CommerceWorkerAgent"]
