"""
Phase 4 — self-evolving skill loop, proven deterministically (no live LLM spend):

  * a task that PASSES verification becomes reusable: the executor saves its
    plan, so the SAME task class second time short-circuits the LLM planner
    (measurable: zero planning LLM calls on the repeat -> cheaper + faster).
  * retrieval-before-task: a matching verified skill doc is injected into
    planning and logged as skill_used.
"""
import asyncio
import json
import uuid

import pytest

from mitchell.core import memory, memory_store
from mitchell.core.tasks import Task, TaskState, TaskStep
from mitchell.core.tool_provider import StaticToolProvider
from helpers import make_fake_llm


@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_store, "DB_PATH", tmp_path / "mitchell.db")
    memory_store.init_db()
    return tmp_path


def _run(coro):
    return asyncio.run(coro)


def test_cache_shortcircuits_repeat_planning(iso_db, monkeypatch):
    # First planning call goes to the LLM; the repeat must NOT.
    calls = {"n": 0}

    async def fake_call(role, messages=None, **kw):
        calls["n"] += 1
        from mitchell.core.llm_client import LLMResult
        content = json.dumps({"steps": [{"description": "s1", "action": "skills.echo"}]})
        return LLMResult(content=content, tool_calls=None)

    from mitchell.core import planner
    monkeypatch.setattr(planner, "call", fake_call)

    t1 = Task(id=str(uuid.uuid4()), instruction="flip the following bit pattern twice")
    _run(planner.create_plan(t1))
    assert calls["n"] == 1, "first plan reached the LLM"
    assert len(t1.steps) == 1

    # Mitchell learned the verified plan -> a repeat must NOT hit the LLM planner.
    memory.save_task_pattern(t1.instruction, [__import__("dataclasses").asdict(s) for s in t1.steps])
    t2 = Task(id=str(uuid.uuid4()), instruction="flip the following bit pattern twice")
    _run(planner.create_plan(t2))
    assert calls["n"] == 1, "repeat planning short-circuited (no LLM call)"
    assert len(t2.steps) == 1


def test_executor_saves_pattern_on_verified_success(iso_db):
    from mitchell.core.executor import execute_task

    instruction = "normalize the incoming csv headers"
    steps = [TaskStep(description="normalize headers", action="skills.normalize")]
    async def pl(task):
        task.steps = steps
        task.save()
        return task

    tid = str(uuid.uuid4())
    t = Task(id=tid, instruction=instruction)
    t.state = TaskState.PENDING
    t.save()
    _run(execute_task(tid, tools=StaticToolProvider(), planner=pl, llm_call=make_fake_llm(final_text="done")))

    final = Task.load(tid)
    assert final.state == TaskState.COMPLETED
    # The verified plan was saved for reuse -> a repeat can short-circuit.
    cached = memory_store.find_cached_plan(instruction)
    assert cached is not None
    assert any("normalize headers" == s.get("description") for s in cached)
    # CRITICAL regression guard: the cached plan is plan-only — it MUST NOT carry
    # execution state, or a "repeat" would reload already-done steps and skip work.
    for s in cached:
        assert "state" not in s, "cached step leaked execution state"
        assert "verification_passed" not in s
        assert "claimed_by" not in s


def test_retrieve_injects_skill_before_task(iso_db):
    from mitchell.core import planner as pl

    # Seed a verified skill doc that matches.
    memory.save_schema("Skill: normalize csv headers",
                       "lowercase + strip each header, collapse duplicates", verified=True)

    async def fake_call(role, messages=None, **kw):
        from mitchell.core.llm_client import LLMResult
        return LLMResult(content=json.dumps({"steps": [{"description": "x", "action": "a"}]}))

    import mitchell.core.planner as planner_mod
    orig = planner_mod.call
    planner_mod.call = fake_call  # minimal shim; restore after
    try:
        t = Task(id=str(uuid.uuid4()), instruction="normalize csv headers please")
        _run(pl.create_plan(t))
    finally:
        planner_mod.call = orig

    # The retrieved skill was logged to the episodic store before the task ran.
    kinds = [e["kind"] for e in memory.list_episodes()]
    assert "skill_used" in kinds
