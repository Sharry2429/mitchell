"""
Planning failure must surface as a hard error, not a silently stuck queue.
If the planner fails, the task goes FAILED — it must NEVER get a fabricated
action="fallback" step that no worker role can claim.
"""
import asyncio
import uuid

import pytest

from mitchell.core.agent_pool import claim_next_step
from mitchell.core.executor import execute_task
from mitchell.core.planner import PlanningError
from mitchell.core.tasks import Task, TaskState
from mitchell.core.tool_provider import StaticToolProvider
from helpers import make_fake_llm


def _run(coro):
    return asyncio.run(coro)


async def _failing_planner(task):
    raise PlanningError("LLM refused to decompose: the goal is gibberish")


def test_planner_failure_marks_task_failed_without_unclaimable_step():
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, instruction="gibberish %$# task")
    task.state = TaskState.PENDING
    task.save()

    _run(
        execute_task(
            task_id,
            tools=StaticToolProvider(),
            planner=_failing_planner,
            llm_call=make_fake_llm(),
        )
    )

    final = Task.load(task_id)
    assert final.state == TaskState.FAILED
    # Crucially: no synthetic "fallback" step was parked on it.
    assert final.steps == []


def test_failed_task_is_not_claimable_and_does_not_deadlock():
    # A failed, step-less task must never be claimable by any worker role.
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, instruction="another bad task")
    task.state = TaskState.FAILED
    task.save()

    for role in ("worker-general", "worker-coder", "worker-operator", "worker-research"):
        idx, step = claim_next_step(task_id, "w", role)
        assert idx is None, f"role {role} claimed a failed task's step"
        assert step is None
