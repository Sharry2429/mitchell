"""Price history, price drops, and availability tracking engine."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class TrackedItem(BaseModel):
    """Product being tracked for price drops."""

    item_id: str
    title: str
    target_price_inr: float
    current_price_inr: float
    lowest_price_inr: float
    highest_price_inr: float
    url: str
    history: List[Dict[str, Any]] = Field(default_factory=list)  # [{"date": "...", "price": ...}]
    alert_triggered: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PriceTracker:
    """Monitors products and alerts user upon price drops."""

    def __init__(self) -> None:
        self.tracker_file = Path(settings.commerce_cache_dir) / "tracked_prices.json"
        self._tracked: Dict[str, TrackedItem] = {}
        self._load()

    def _load(self) -> None:
        """Load tracked items from disk."""
        if self.tracker_file.exists():
            try:
                data = json.loads(self.tracker_file.read_text(encoding="utf-8"))
                for i_id, i_data in data.items():
                    self._tracked[i_id] = TrackedItem.model_validate(i_data)
            except Exception as e:
                logger.warning("Failed to load tracked prices: {}", e)

    def _save(self) -> None:
        """Persist tracked items to disk."""
        try:
            self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.model_dump(mode="json") for k, v in self._tracked.items()}
            self.tracker_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save tracked prices: {}", e)

    def track_product(self, title: str, current_price: float, target_price: float, url: str) -> TrackedItem:
        """Add a product to active price monitoring."""
        import uuid
        item_id = f"item_{str(uuid.uuid4())[:8]}"
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        item = TrackedItem(
            item_id=item_id,
            title=title,
            target_price_inr=target_price,
            current_price_inr=current_price,
            lowest_price_inr=current_price,
            highest_price_inr=current_price,
            url=url,
            history=[{"date": today_str, "price": current_price}],
        )
        self._tracked[item_id] = item
        self._save()

        event_log.log_event(
            "price_tracking_started",
            source="price_tracker",
            data={"title": title, "current": current_price, "target": target_price},
        )
        logger.info("Price tracking registered for '{}' (Target: ₹{})", title, target_price)
        return item

    def list_tracked(self) -> List[Dict[str, Any]]:
        """List all currently monitored products."""
        return [item.model_dump(mode="json") for item in self._tracked.values()]


price_tracker = PriceTracker()

__all__ = ["TrackedItem", "PriceTracker", "price_tracker"]
