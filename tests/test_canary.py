"""
Canary suite — catches verification silently regressing.

Feeds a KNOWN-CORRECT build and a KNOWN-BROKEN build through the real
execute_task pipeline. Correct must pass verification (task COMPLETED) and
broken must fail it (task FAILED). If either flips, the Phase 1 wall is broken.
"""
import asyncio
import uuid

from mitchell.core.executor import execute_task
from mitchell.core.tasks import Task, TaskState, TaskStep
from mitchell.core.tool_provider import StaticToolProvider
from helpers import make_fake_llm, make_planner


def _run(coro):
    return asyncio.run(coro)


def _build_step_task(target):
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, instruction="produce a build artifact")
    task.state = TaskState.PENDING
    task.save()
    step = TaskStep(
        description="write the build artifact",
        action="windows.fs.write_file",
        args={"expect_file_exists": str(target)},
    )
    return task_id, make_planner([step])


def test_canary_correct_build_passes(tmp_path):
    target = tmp_path / "build.txt"
    task_id, planner = _build_step_task(target)

    # Correct: the tool genuinely writes the artifact the step declares.
    tools = StaticToolProvider(
        {"write_build": lambda path, content: open(path, "w").write(content)}
    )
    llm = make_fake_llm(first_tool=("write_build", {"path": str(target), "content": "ok"}))

    _run(execute_task(task_id, tools=tools, planner=planner, llm_call=llm))

    final = Task.load(task_id)
    assert target.exists(), "canary tool did not actually write the file"
    assert final.state == TaskState.COMPLETED, "known-correct build FAILED canary"
    assert final.steps[0].verification_passed is True


def test_canary_broken_build_fails(tmp_path):
    target = tmp_path / "build.txt"
    task_id, planner = _build_step_task(target)

    # Broken: the tool surface does NOT provide the tool, so execution errors.
    tools = StaticToolProvider({})  # no write_build registered
    llm = make_fake_llm(first_tool=("write_build", {"path": str(target), "content": "ok"}))

    _run(execute_task(task_id, tools=tools, planner=planner, llm_call=llm))

    final = Task.load(task_id)
    assert final.state == TaskState.FAILED, "known-broken build PASSED canary (verification regressed)"
    assert not final.steps[0].verification_passed
