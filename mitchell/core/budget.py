"""
mitchell.core.budget
====================
Budget enforcement for LLM calls.

``check_budget_before_call`` is called by the LLM client before every model
call. It sums the REAL, persistently-logged spend (from tokens.jsonl, which
records actual model + token counts priced via the routing table) and refuses
the call with ``BudgetExceeded`` once the threshold is hit. This is a hard
cap, not a suggestion: the meter reads the log, not an in-memory guess, so it
survives restarts and cannot be bypassed by forgetting to increment a counter.

Basic threshold refusal only. Cost-aware downgrade routing (swap the tier in
mid-flight near the cap) is a later refinement — deliberately out of scope now.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

BUDGET_CAP = float(os.environ.get("MITCHELL_BUDGET_CAP", "5.0"))


class BudgetExceeded(Exception):
    pass


def _tokens_log_path() -> Path:
    return Path(os.path.expanduser("~/.system-mcp/tokens.jsonl"))


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Basic cost estimation (fallback pricing if not in a strict registry)."""
    # Simple fallback pricing (e.g. general 1M token cost)
    input_price = 0.5
    output_price = 1.5
    return (prompt_tokens / 1_000_000) * input_price + (completion_tokens / 1_000_000) * output_price


def total_spend() -> float:
    """Sum of real logged cost across all recorded calls (durable)."""
    p = _tokens_log_path()
    if not p.exists():
        return 0.0
    total = 0.0
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                total += float(json.loads(line).get("cost_estimate", 0.0))
            except (ValueError, json.JSONDecodeError):
                continue
    return total


def remaining_budget() -> float:
    return max(0.0, BUDGET_CAP - total_spend())


def check_budget_before_call(role: str, task_id: str | None = None) -> float:
    """Raise BudgetExceeded if logged spend has reached the cap. Returns spend."""
    spent = total_spend()
    if spent >= BUDGET_CAP:
        raise BudgetExceeded(
            f"Budget cap ${BUDGET_CAP:.2f} reached (${spent:.2f} spent). "
            f"Refusing call for role='{role}'."
        )
    return spent


def log_usage(task_id: str | None, role: str, model: str, prompt_tokens: int, completion_tokens: int, cost_estimate: float):
    p = _tokens_log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        log_entry = {
            "task_id": task_id,
            "role": role,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_estimate": round(cost_estimate, 6),
        }
        f.write(json.dumps(log_entry) + "\n")
