"""Token and cost tracking engine with real-time INR (₹) conversion and budget caps."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger

# Approximate pricing per 1M tokens in USD
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # Grok (xAI)
    "grok-2": {"input": 2.00, "output": 10.00},
    "grok-beta": {"input": 5.00, "output": 15.00},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Anthropic
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    # Gemini
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # Fallback default
    "default": {"input": 0.50, "output": 1.50},
}

USD_TO_INR_RATE = 84.50  # Default exchange rate


class UsageRecord(BaseModel):
    """Record of a single model inference call."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    cost_inr: float
    purpose: str = "general"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CostTracker:
    """Tracks token consumption, calculates costs in USD and INR (₹), and enforces budget caps."""

    def __init__(
        self,
        daily_budget_inr: float = 500.0,
        monthly_budget_inr: float = 10000.0,
        exchange_rate: float = USD_TO_INR_RATE,
    ) -> None:
        self.daily_budget_inr = daily_budget_inr
        self.monthly_budget_inr = monthly_budget_inr
        self.exchange_rate = exchange_rate
        self.storage_file = Path(settings.data_dir) / "cost_usage.json"
        self._records: List[UsageRecord] = []
        self._load()

    def _load(self) -> None:
        if self.storage_file.exists():
            try:
                with self.storage_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._records = [UsageRecord.model_validate(r) for r in data.get("records", [])]
            except Exception as e:
                logger.warning("Error reading cost_usage.json: {}", e)

    def _save(self) -> None:
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_file.open("w", encoding="utf-8") as f:
                json.dump(
                    {"records": [r.model_dump(mode="json") for r in self._records[-500:]]},
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error("Error saving cost_usage.json: {}", e)

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Tuple[float, float]:
        """Calculate USD and INR cost for token counts."""
        pricing = MODEL_PRICING.get(model.lower(), MODEL_PRICING["default"])
        input_cost = (prompt_tokens / 1_000_000.0) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000.0) * pricing["output"]
        cost_usd = round(input_cost + output_cost, 6)
        cost_inr = round(cost_usd * self.exchange_rate, 4)
        return cost_usd, cost_inr

    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        purpose: str = "general",
    ) -> UsageRecord:
        """Record model usage and cost."""
        total_tokens = prompt_tokens + completion_tokens
        cost_usd, cost_inr = self.calculate_cost(model, prompt_tokens, completion_tokens)

        rec = UsageRecord(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            cost_inr=cost_inr,
            purpose=purpose,
        )
        self._records.append(rec)
        self._save()

        event_log.log_event(
            "llm_cost_recorded",
            source="cost_tracker",
            data={
                "model": model,
                "tokens": total_tokens,
                "cost_inr": f"₹{cost_inr:.4f}",
                "cost_usd": f"${cost_usd:.6f}",
                "purpose": purpose,
            },
        )
        return rec

    def get_daily_total_inr(self) -> float:
        """Calculate total spend in INR for today (UTC)."""
        today = datetime.now(timezone.utc).date()
        today_records = [r for r in self._records if r.timestamp.date() == today]
        return round(sum(r.cost_inr for r in today_records), 2)

    def is_budget_exceeded(self) -> bool:
        """Check if daily budget cap has been reached."""
        return self.get_daily_total_inr() >= self.daily_budget_inr

    def get_summary(self) -> Dict[str, Any]:
        """Return spending summary in INR and USD."""
        total_inr = round(sum(r.cost_inr for r in self._records), 2)
        total_usd = round(sum(r.cost_usd for r in self._records), 4)
        total_tokens = sum(r.total_tokens for r in self._records)
        daily_inr = self.get_daily_total_inr()

        return {
            "total_spent_inr": f"₹{total_inr:.2f}",
            "today_spent_inr": f"₹{daily_inr:.2f}",
            "daily_budget_inr": f"₹{self.daily_budget_inr:.2f}",
            "total_spent_usd": f"${total_usd:.4f}",
            "total_tokens": total_tokens,
            "budget_status": "EXCEEDED" if self.is_budget_exceeded() else "OK",
        }


cost_tracker = CostTracker()

__all__ = ["CostTracker", "cost_tracker", "UsageRecord", "MODEL_PRICING", "USD_TO_INR_RATE"]
