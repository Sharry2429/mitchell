"""
mitchell.core.executor
======================
Walks a Task's dependency graph, dispatches steps to workers, and gates each
step behind Phase 1 verification.

Decoupled from the tool surface: the executor talks to a ``ToolProvider``
interface (FastMCP server in production, static/in-process or subprocess
providers in tests/Phase 6) — never to the live server object directly.

Planning is wired here: a task with no steps is decomposed via the planner
before any step can be claimed. A planning failure marks the task FAILED
rather than parking an unclaimable step.
"""
from __future__ import annotations

import asyncio
import json
import time

from mitchell.core.agent_pool import (
    DeviceLock,
    claim_next_step,
    mark_step_completed,
    mark_step_failed,
)

from mitchell.providers.base import LLMResult
from mitchell.providers.registry import cascading_call
from mitchell.core.planner import PlanningError, create_plan
from mitchell.core.tasks import Task, TaskState, TaskStep, list_tasks, task_all_terminal
from mitchell.core.tool_provider import MCPToolProvider, ToolProvider
from mitchell.core.verify import verify_step  # hard import: missing => ImportError at load

# Sentinel for "use the real LLM client" — lets tests inject a deterministic call.
async def _REAL_CALL(tier, messages, tools, task_id):
    return await cascading_call(tier, messages=messages, tools=tools, task_id=task_id)


def _safe_log_episode(task_id, kind, summary, **kw):
    """Best-effort ground-truth logging — stripped for v1."""
    pass


def _pattern_key(step: TaskStep) -> str | None:
    """A stable pattern key for a step so promotion can cluster like episodes."""
    if step.action:
        return step.action
    if step.description:
        words = step.description.split()
        return " ".join(words[:4]) if words else None
    return None


def _steps_to_dicts(steps: list[TaskStep]) -> list[dict]:
    """Serialize ONLY the planning-relevant fields (never execution state).

    Persisting state/completed/verification would make a cached "repeat" reload
    already-done steps and silently skip real work. A reusable plan must re-run
    from PENDING, so we keep just what defines the plan.
    """
    return [
        {
            "description": s.description,
            "action": s.action,
            "args": s.args,
            "depends_on": list(s.depends_on),
        }
        for s in steps
    ]


async def _llm_tool_loop(
    task_id: str,
    step: TaskStep,
    worker_role: str,
    tools: ToolProvider,
    llm_call,
) -> list[dict]:
    """Run the agent/tool turn loop for one step. Returns the full transcript."""
    tier = "executor"  # model-routing plan: GPT-OSS chain -> AiCredits net
    openai_tools = await tools.list_tools_openai()

    prompt = (
        f"Execute step: {step.description}\n"
        f"Needed action namespace: {step.action}\n"
        f"Previous error (if any): {step.error}"
    )
    messages: list[dict] = [{"role": "user", "content": prompt}]

    max_turns = 10
    for _ in range(max_turns):
        if worker_role == "worker-operator":
            with DeviceLock():
                result: LLMResult = await llm_call(
                    tier, messages=messages, tools=openai_tools, task_id=task_id
                )
        else:
            result: LLMResult = await llm_call(
                tier, messages=messages, tools=openai_tools, task_id=task_id
            )

        messages.append(
            {
                "role": "assistant",
                "content": result.content,
                "tool_calls": result.tool_calls,
            }
        )

        if not result.tool_calls:
            break

        for tcall in result.tool_calls:
            tool_res_str = ""
            try:
                args = json.loads(tcall.function.arguments or "{}")
            except Exception:  # noqa: BLE001
                args = {}
            try:
                tool_res_str = await tools.call_tool(tcall.function.name, args)
            except Exception as e:  # noqa: BLE001
                tool_res_str = f"Error executing tool: {e}"

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tcall.id,
                    "name": tcall.function.name,
                    "content": tool_res_str,
                }
            )

    return messages


async def run_step(
    task_id: str,
    step: TaskStep,
    worker_role: str,
    tools: ToolProvider | None = None,
    llm_call=None,
) -> bool:
    """Execute one step with retries, then gate it behind real verification."""
    tools = tools or MCPToolProvider()
    llm_call = llm_call or _REAL_CALL

    max_retries = 2
    for attempt in range(max_retries + 1):
        tier = "executor"  # same chain for all attempts; retries are loop-level
        try:
            messages = await _llm_tool_loop(task_id, step, worker_role, tools, llm_call)
        except Exception as e:  # noqa: BLE001
            step.error = f"Execution error on attempt {attempt + 1}: {e}"
            continue

        # Hard gate: verification failure is a retry/fail, never a pass.
        verified = verify_step(step, messages)
        if verified:
            step.verification_passed = True
            return True

        step.error = f"Verification failed on attempt {attempt + 1}"

    return False


async def _plan_if_needed(task: Task, planner) -> Task:
    """Ensure a task has steps; mark it FAILED (not stuck) if planning fails."""
    if task.steps:
        return task
    try:
        return await planner(task)
    except PlanningError as e:
        print(f"⚠️  Planning failed for task {task.id}: {e}")
        task.state = TaskState.FAILED
        task.save()
        return task
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  Unexpected planning error for task {task.id}: {e}")
        task.state = TaskState.FAILED
        task.save()
        return task


async def _process_task(
    worker_id: str,
    worker_role: str,
    task: Task,
    tools: ToolProvider,
    planner,
    llm_call,
) -> bool:
    """Run a single task to completion. Returns True if it reached a terminal state."""
    task = await _plan_if_needed(task, planner)
    if task.state == TaskState.FAILED:
        return True  # planning failed -> terminal (FAILED), not stuck

    while True:
        step_idx, step = claim_next_step(task.id, worker_id, worker_role)
        if step is None:
            break

        try:
            success = await run_step(task.id, step, worker_role, tools, llm_call)
        except Exception as e:  # noqa: BLE001 - never let one step kill the worker
            success = False
            step.error = f"Unexpected step error: {e}"

        if success:
            # Persist the verification result so it survives the reload in mark_*.
            mark_step_completed(task.id, step_idx, verification_passed=True)
        else:
            mark_step_failed(task.id, step_idx, step.error or "Failed after retries")

        # Ground-truth episodic log: what actually happened, gated by whether
        # verification passed. Only verified episodes can later be promoted.
        _safe_log_episode(
            task.id,
            kind="step",
            summary=f"{'PASS' if success else 'FAIL'} step: {step.description}",
            verified=success,
            pattern_key=_pattern_key(step),
            data={"action": step.action, "error": step.error},
        )

    # Finalize task state once every step is terminal.
    live = Task.load(task.id)
    if live and task_all_terminal(live):
        live.state = (
            TaskState.COMPLETED
            if any(s.state == TaskState.COMPLETED for s in live.steps)
            and not any(s.state == TaskState.FAILED for s in live.steps)
            else TaskState.FAILED
        )
        live.completed_at = time.time()
        live.save()
        print(
            f"✅ Task {live.id} finished: {live.state} "
            f"({len(live.steps)} steps)"
        )
        _safe_log_episode(live.id, kind="task", summary=f"task {live.state}", verified=(live.state == TaskState.COMPLETED))

        # Memory persistence disabled for v1
    return True


async def execute_task(
    task_id: str,
    *,
    tools: ToolProvider | None = None,
    planner=None,
    llm_call=None,
) -> bool:
    """Run one specific task to completion (single-shot, no infinite loop)."""
    tools = tools or MCPToolProvider()
    planner = planner or create_plan
    llm_call = llm_call or _REAL_CALL

    task = Task.load(task_id)
    if task is None:
        raise FileNotFoundError(f"Task {task_id} not found")
    return await _process_task("runner", "worker-general", task, tools, planner, llm_call)


def recover_interrupted_tasks() -> int:
    """Resume after an unexpected kill/restart.

    A task whose steps were left in RUNNING state (claimed just before the
    process died) can never be reclaimed by claim_next_step — it would stay
    stuck forever. This resets those steps to PENDING so a restarting worker
    re-claims and re-runs them, and logs an 'interrupt' episode into the
    ground-truth log so the restart has context instead of starting cold.

    Returns the number of interrupted tasks recovered.
    """
    recovered = 0
    for task in list_tasks():
        interrupted = any(s.state == TaskState.RUNNING for s in task.steps)
        if not interrupted:
            continue
        for step in task.steps:
            if step.state == TaskState.RUNNING:
                step.state = TaskState.PENDING
                step.claimed_by = None
                step.claimed_at = None
        task.state = TaskState.RUNNING if task.state == TaskState.RUNNING else task.state
        task.save()
        recovered += 1
        _safe_log_episode(
            task.id,
            kind="interrupt",
            summary="process interrupted mid-task; steps reset to PENDING for retry",
            verified=False,
        )
    return recovered


async def run_worker_once(worker_id: str, worker_role: str, *, tools=None, planner=None, llm_call=None):
    """Recover interrupted tasks, then run the worker (single-task or queue mode)."""
    n = recover_interrupted_tasks()
    if n:
        print(f"♻️  Recovered {n} interrupted task(s) from the last session")
    await worker_loop(worker_id, worker_role, tools=tools, planner=planner, llm_call=llm_call)


async def worker_loop(
    worker_id: str,
    worker_role: str,
    task_id: str | None = None,
    *,
    tools: ToolProvider | None = None,
    planner=None,
    llm_call=None,
):
    """Worker pool loop.

    If ``task_id`` is given, process that single task and return. Otherwise
    scan the task queue for PENDING/RUNNING tasks and process them, sleeping
    when idle. The real task ids come from the queue — never a hardcoded stub.
    """
    tools = tools or MCPToolProvider()
    planner = planner or create_plan
    llm_call = llm_call or _REAL_CALL

    if task_id is not None:
        task = Task.load(task_id)
        if task is None:
            print(f"Task {task_id} not found")
            return
        await _process_task(worker_id, worker_role, task, tools, planner, llm_call)
        return

    while True:
        worked = False
        for task in list_tasks():
            if task.state in (TaskState.PENDING, TaskState.RUNNING):
                await _process_task(worker_id, worker_role, task, tools, planner, llm_call)
                worked = True
        if not worked:
            await asyncio.sleep(1)
