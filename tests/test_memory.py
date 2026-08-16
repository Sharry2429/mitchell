"""
Phase 3 memory proofs:
  * three stores behave correctly (episodic append-only, semantic upsert,
    procedural save/retrieve)
  * promotion mechanic is gated on Phase 1 verification BY CONSTRUCTION
    (unverified episodes never promote)
  * interrupt recovery: a task killed mid-step resumes, not starts cold
"""
import asyncio
import uuid

import pytest

from mitchell.core import memory, memory_store
from mitchell.core.executor import (
    execute_task,
    recover_interrupted_tasks,
    worker_loop,
)
from mitchell.core.tasks import Task, TaskState, TaskStep
from mitchell.core.tool_provider import StaticToolProvider
from helpers import make_fake_llm, make_planner


@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    """Isolate the SQLite DB to a temp file per test."""
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_store, "DB_PATH", tmp_path / "mitchell.db")
    memory_store.init_db()
    return tmp_path


def _run(coro):
    return asyncio.run(coro)


# ---- the three stores ------------------------------------------------------

def test_episodic_is_append_only(iso_db):
    a = memory.log_episode("t1", "step", "PASS step: build", verified=True, pattern_key="build")
    b = memory.log_episode("t1", "step", "PASS step: test", verified=True, pattern_key="test")
    c = memory.log_episode("t1", "step", "FAIL step: x", verified=False, pattern_key="x")
    eps = memory.list_episodes()
    assert len(eps) == 3
    assert eps[0]["id"] == a < b < c  # append-only, monotonic
    # verified filter works
    assert len(memory.list_episodes(verified=True)) == 2
    assert len(memory.list_episodes(verified=False)) == 1


def test_semantic_upserts_not_appends(iso_db):
    memory.remember_semantic("device.os", "windows")
    assert memory.recall_semantic("device.os") == "windows"
    # reality changed -> replaced, not a second entry
    memory.remember_semantic("device.os", "android")
    assert memory.recall_semantic("device.os") == "android"
    assert memory.recall_semantic("device.os") != "windows"
    assert len(memory.all_semantic()) == 1


def test_procedural_save_and_retrieve(iso_db):
    memory.save_schema("Skill: parse build tool", "Use regex to pull version from build output.", verified=True)
    hit = memory.retrieve_schema("parse build output version")
    assert hit is not None
    assert "build" in hit["title"] or "regex" in hit["body"]


# ---- promotion gated on verification --------------------------------------

def test_promotion_only_from_verified_episodes(iso_db):
    # Three VERIFIED episodes share a pattern -> promotes.
    for _ in range(3):
        memory.log_episode("t", "step", "PASS step: sync device time", verified=True, pattern_key="sync_time")
    promoted = memory.promote_verified_patterns(min_occurrences=3)
    assert len(promoted) == 1
    assert any("sync time" in t for t in promoted)
    # And it's now retrievable before a future task.
    assert memory.retrieve_schema("sync device time") is not None


def test_unverified_episode_blocks_promotion(iso_db):
    # Same pattern, but one episode FAILED verification -> whole cluster blocked.
    for _ in range(2):
        memory.log_episode("t", "step", "PASS step: reformat code", verified=True, pattern_key="reformat_code")
    memory.log_episode("t", "step", "FAIL step: reformat code", verified=False, pattern_key="reformat_code")
    promoted = memory.promote_verified_patterns(min_occurrences=2)
    assert promoted == []
    assert memory.list_schemas(verified=True) == []
    # No skill doc was laundered from a run that didn't actually work.


# ---- interrupt recovery (resume, not cold start) ---------------------------

def _build_interrupted_task():
    tid = str(uuid.uuid4())
    t = Task(id=tid, instruction="resumable task")
    t.state = TaskState.RUNNING
    t.steps = [TaskStep(description="step one", action="skills.echo", state=TaskState.COMPLETED),
               TaskStep(description="step two", action="skills.echo", state=TaskState.RUNNING,
                        claimed_by="w-dead", claimed_at=1.0),
               TaskStep(description="step three", action="skills.echo", state=TaskState.PENDING)]
    t.save()
    return tid


def test_recover_resets_running_steps(iso_db):
    tid = _build_interrupted_task()
    assert recover_interrupted_tasks() >= 1
    t = Task.load(tid)
    # The mid-flight running step is back to PENDING and unclaimed -> reclaimable.
    assert t.steps[1].state == TaskState.PENDING
    assert t.steps[1].claimed_by is None


def test_resume_completes_interrupted_task(iso_db):
    tid = _build_interrupted_task()
    recover_interrupted_tasks()

    planner = make_planner([])  # already has steps; planner not needed but injected
    llm = make_fake_llm(final_text="ok")
    _run(worker_loop("w-neww", "worker-general", tid, tools=StaticToolProvider(), planner=planner, llm_call=llm))

    final = Task.load(tid)
    assert final.state == TaskState.COMPLETED
    assert all(s.state == TaskState.COMPLETED for s in final.steps)
    # The interruption was recorded in the ground-truth log.
    kinds = {e["kind"] for e in memory.list_episodes()}
    assert "interrupt" in kinds
