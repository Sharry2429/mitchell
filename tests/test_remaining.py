"""
Remaining-build (Phases 10/11/13/14/15 + L2-4 + routing) — deterministic tests,
LLM mocked, no paid calls.
"""
import asyncio
import os
import uuid

import pytest

from mitchell.core.llm_client import LLMResult


def _run(coro):
    return asyncio.run(coro)


def _llm_script(script):
    """Return an llm_call that pops from a list of contents."""
    state = {"i": 0}
    async def fake(role, messages=None, tools=None, task_id=None):
        i = state["i"]; state["i"] += 1
        c = script[i] if i < len(script) else script[-1]
        return LLMResult(content=c, tool_calls=None)
    return fake


# ------------------------- WATCHDOG (Phase 10) ------------------------ #

def test_watchdog_thresholds(monkeypatch):
    import mitchell.core.watchdog as w
    monkeypatch.setattr(w, "laptop_battery", lambda: {"has_battery": True, "percent": 40, "charging": False})
    monkeypatch.setattr(w, "phone_battery", lambda: 15)
    alerts = w.check_thresholds()
    assert any("Laptop at 40%" in a for a in alerts)
    assert any("Phone at 15%" in a for a in alerts)


def test_watchdog_no_alert_when_healthy(monkeypatch):
    import mitchell.core.watchdog as w
    monkeypatch.setattr(w, "laptop_battery", lambda: {"has_battery": True, "percent": 90, "charging": True})
    monkeypatch.setattr(w, "phone_battery", lambda: 80)
    assert w.check_thresholds() == []


# ------------------------- REVIEW (Phase 11) -------------------------- #

def test_review_pipeline_order():
    from mitchell.core import review
    # iterative mid loop: 1 issue then NO_ISSUES (fresh fake per call)
    issues = _run(review.iterative_review("let code = input;",
                                          llm_call=_llm_script(["issue: handle empty input", "NO_ISSUES"])))
    assert len(issues) == 1 and "empty input" in issues[0]
    # final once, expensive
    final = _run(review.final_review("let code = input;", llm_call=_llm_script(["APPROVED"])))
    assert "APPROVED" in final.upper()
    # full run: 1 iterative issue -> 1 fix task; APPROVED final adds none
    res = _run(review.run_review("let code = input;",
                                 llm_call=_llm_script(["issue: handle empty input", "NO_ISSUES", "APPROVED"])))
    assert len(res["iterative_issues"]) == 1
    assert len(res["fix_task_ids"]) == 1

# ------------------------- SELF-REPAIR (Phase 13) --------------------- #

def test_self_repair_detect(iso_mem):
    from mitchell.core import memory, self_repair
    memory.log_episode("t", "task", "task failed", verified=False)
    memory.log_episode("t", "task", "task completed", verified=True)
    sigs = self_repair.detect()
    assert len(sigs) == 1 and sigs[0]["kind"] == "task"


def test_self_repair_fixed_when_verify_passes(tmp_path):
    from mitchell.core import self_repair
    llm = _llm_script(["patch: add a null check"])
    res = _run(self_repair.bounded_escalate(
        str(tmp_path), "crash: NoneType at line 3", llm_call=llm,
        verify=lambda sb: {"ok": True}, max_attempts=3))
    assert res["status"] == "fixed" and res["attempts"] == 1


def test_self_repair_escalates_when_unfixable(tmp_path):
    from mitchell.core import self_repair
    llm = _llm_script(["patch a", "patch b", "patch c", "patch d"])
    res = _run(self_repair.bounded_escalate(
        str(tmp_path), "unfixable bug", llm_call=llm,
        verify=lambda sb: {"ok": False}, max_attempts=3))
    assert res["status"] == "escalated" and res["attempts"] == 3


# ------------------------- SELF-OPTIMIZE (Phase 14) ------------------- #

def test_self_optimize_ground_truth(tmp_path, monkeypatch):
    import json
    from mitchell.core import self_optimize
    log = tmp_path / "tokens.jsonl"
    line = json.dumps({"role": "base", "cost_estimate": 0.4, "prompt_tokens": 1000})
    with open(log, "w", encoding="utf-8") as f:
        f.writelines((line + "\n") * 12)
    monkeypatch.setattr(self_optimize, "TOKENS_LOG", str(log))
    stats = self_optimize.analyze_ground_truth()
    assert stats["base"]["calls"] == 12
    assert stats["base"]["cost"] == pytest.approx(4.8)
    suggs = self_optimize.config_suggestion(stats)
    assert any(s["role"] == "base" for s in suggs)


# ------------------------- BUTLER (Phase 15) -------------------------- #

def test_butler_startup_register_idempotent(monkeypatch, tmp_path):
    from mitchell.core import butler
    monkeypatch.setattr(os, "environ", {**os.environ, "APPDATA": str(tmp_path)})
    p1 = butler.ensure_startup_register()
    assert p1 is not None and os.path.exists(p1)
    p2 = butler.ensure_startup_register()
    assert p1 == p2  # idempotent: same entry, not recreated
    assert os.path.exists(p1)


def test_butler_once_recovers(monkeypatch):
    from mitchell.core import butler, executor, watchdog
    monkeypatch.setattr(executor, "recover_interrupted_tasks", lambda: 2)
    monkeypatch.setattr(watchdog, "run_once", lambda: ["[POWER] Laptop low"])
    res = butler.run_butler_once()
    assert res["recovered"] == 2
    assert res["watchdog_alerts"] == ["[POWER] Laptop low"]


# ------------------------- ROUTING DOWNGRADE -------------------------- #

def test_select_model_downgrade_at_low_budget():
    from mitchell.core.models import select_model, MODEL_TIERS
    base = MODEL_TIERS["base"]
    downgraded = select_model("base", remaining_budget=0.2)
    # deepseek is the cheapest per output price -> cost-aware downgrade picks it
    assert downgraded == "deepseek/deepseek-v4-flash"
    # at healthy budget, keep the normal mapping
    assert select_model("base", remaining_budget=5.0) == base


def test_vision_role_never_downgraded():
    from mitchell.core.models import select_model, MODEL_TIERS
    for role in ("ui_vision", "general_vision"):
        assert select_model(role, remaining_budget=0.01) == MODEL_TIERS[role]


# ------------------------- VERIFY LEVELS 2-4 -------------------------- #

def test_verify_rubric():
    from mitchell.core.tasks import TaskStep
    from mitchell.core.verify import verify_against_rubric
    tr = [{"role": "assistant", "content": "Fixed the overflow and added tests for the boundary"}]
    r = verify_against_rubric(TaskStep(description="x"), tr, ["overflow", "tests"])
    assert r["passed"] is True and len(r["matched"]) == 2


def test_adversarial_review_approved():
    from mitchell.core.verify import adversarial_review
    llm = _llm_script(["APPROVED"])
    passed, issues = _run(adversarial_review([{"role": "assistant", "content": "done"}], llm_call=llm))
    assert passed is True and issues == []


def test_adversarial_review_flags_issues():
    from mitchell.core.verify import adversarial_review
    llm = _llm_script(["Race condition on line 12\nMissing validation"])
    passed, issues = _run(adversarial_review([{"role": "assistant", "content": "done"}], llm_call=llm))
    assert passed is False and len(issues) >= 1


def test_device_verify_vacuous_when_no_expectation():
    from mitchell.core.tasks import TaskStep
    from mitchell.core.verify import device_verify
    assert device_verify(TaskStep(description="x", args={})) is True


@pytest.fixture
def iso_mem(tmp_path, monkeypatch):
    from mitchell.core import memory_store
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_store, "DB_PATH", tmp_path / "m.db")
    memory_store.init_db()
    return tmp_path
