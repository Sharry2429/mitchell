"""
Budget enforcement: real per-model cost from the routing table, and a hard
refusal once the cap is hit. The meter reads the persisted log, so it cannot
be bypassed by forgetting to increment an in-memory counter.
"""
import asyncio
import json
import uuid

import pytest

from mitchell.core import budget
from mitchell.core.budget import BudgetExceeded, check_budget_before_call, estimate_cost, log_usage


def _run(coro):
    return asyncio.run(coro)


def test_estimate_cost_uses_real_per_model_pricing():
    # deepseek/deepseek-v4-flash: $0.02 / $0.05 per 1M tokens
    cost = estimate_cost("deepseek/deepseek-v4-flash", 1_000_000, 1_000_000)
    assert cost == pytest.approx(0.07)
    # Sol is more expensive than flash — different models, different real cost.
    sol = estimate_cost("openai/gpt-5.6-sol", 1_000_000, 1_000_000)
    assert sol > cost


def test_check_budget_refuses_when_cap_reached(tmp_path, monkeypatch):
    # Isolate the meter to a temp log and a tiny cap.
    log_path = tmp_path / "tokens.jsonl"
    monkeypatch.setattr(budget, "_tokens_log_path", lambda: log_path)
    monkeypatch.setattr(budget, "BUDGET_CAP", 1.0)

    # First call: under cap -> allowed.
    spend = check_budget_before_call("base", task_id=None)
    assert spend == 0.0

    # Bog the persisted log down with a real, priced usage entry past the cap.
    log_usage("t1", "base", "openai/gpt-5.6-luna", 20_000_000, 0, estimate_cost("openai/gpt-5.6-luna", 20_000_000, 0))
    assert budget.total_spend() == pytest.approx(3.0)  # $0.15/M * 20M = $3.00

    # Once persisted spend exceeds the cap, the next call is refused.
    monkeypatch.setattr(budget, "BUDGET_CAP", 2.0)
    with pytest.raises(BudgetExceeded):
        check_budget_before_call("base", task_id="t2")
