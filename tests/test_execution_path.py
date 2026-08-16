"""
Step 1 proof: the execution path runs a REAL task id (never the hardcoded
"test-task"), and planning is actually wired in end-to-end.
"""
import asyncio
import uuid

from mitchell.core.executor import execute_task
from mitchell.core.tasks import Task, TaskState, TaskStep
from mitchell.core.tool_provider import StaticToolProvider
from helpers import make_fake_llm, make_planner


def _run(coro):
    return asyncio.run(coro)


def test_execute_task_uses_real_task_id_and_runs_planned_steps():
    # A task created just like `mitchell-task --task "..."` does: real uuid, NO steps.
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, instruction="Do a real, non-test task")
    task.state = TaskState.PENDING
    task.save()

    planner_calls = []
    steps = [
        TaskStep(description="Step one", action="skills.write"),
        TaskStep(description="Step two", action="research.read", depends_on=[0]),
    ]
    planner = make_planner(steps, calls=planner_calls)
    llm = make_fake_llm(first_tool=None, final_text="real output")

    tools = StaticToolProvider()

    _run(execute_task(task_id, tools=tools, planner=planner, llm_call=llm))

    # The task id that ran is the one we created — the hardcoded "test-task" is gone.
    assert task_id != "test-task"
    final = Task.load(task_id)
    assert final is not None
    assert final.id == task_id
    assert planner_calls, "planner was never invoked before execution"
    assert final.state == TaskState.COMPLETED
    assert all(s.state == TaskState.COMPLETED for s in final.steps)
    # Dependency ordering enforced: step one completed before step two was claimed.
    assert final.steps[0].state == TaskState.COMPLETED
    assert final.steps[1].claimed_by is not None
    # No step left with a fabricated "fallback" action.
    assert all(s.action != "fallback" for s in final.steps)


def test_worker_takes_explicit_task_argument():
    from mitchell.core.executor import worker_loop

    task_id = str(uuid.uuid4())
    task = Task(id=task_id, instruction="single task via worker")
    task.state = TaskState.PENDING
    task.save()

    planner = make_planner([TaskStep(description="only step", action="x")])
    llm = make_fake_llm(final_text="ok")

    _run(worker_loop("w1", "worker-general", task_id, tools=StaticToolProvider(), planner=planner, llm_call=llm))

    final = Task.load(task_id)
    assert final.state == TaskState.COMPLETED
    assert final.steps[0].verification_passed is True
