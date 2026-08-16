import json
from mitchell.core.tasks import Task, TaskStep
from mitchell.providers.registry import cascading_call as call

def find_cached_plan(instruction): return None
def get_user_profile(): return "General User"
def get_skills_log(): return "No custom skills"
def retrieve_schema(instruction): return None
def log_episode(*args, **kwargs): pass


class PlanningError(Exception):
    """Raised when a task cannot be decomposed into steps.

    A planning failure must surface as a hard, observable error — NOT as a
    synthetic ``action="fallback"`` step that no worker role can ever claim
    (which silently deadlocks the queue). Callers mark the task FAILED and
    stop; they do not park an unclaimable step.
    """


async def create_plan(task: Task) -> Task:
    # Phase 4 retrieval: reuse a verified procedural skill doc BEFORE deriving
    # a fresh approach, so a task class Mitchell already solved doesn't re-derive it.
    skill = retrieve_schema(task.instruction)
    skill_context = ""
    if skill:
        skill_context = (
            "\n\nKNOWN-SKILL (a verified approach Mitchell already solved):\n"
            f"Title: {skill['title']}\n{skill['body']}"
        )
        try:
            log_episode(task.id, "skill_used",
                        f"retrieved skill before task: {skill['title']}",
                        verified=True, pattern_key="skill_retrieval")
        except Exception:  # noqa: BLE001
            pass

    # Check cache first: a previously-verified plan short-circuits the LLM
    # entirely (measurably cheaper + faster the second time).
    cached_steps = find_cached_plan(task.instruction)
    if cached_steps:
        # Reconstruct TaskStep objects
        task.steps = [TaskStep(**s) for s in cached_steps]
        task.save()
        return task

    # No cache hit, call LLM
    profile = get_user_profile()
    skills = get_skills_log()
    
    prompt = f"""You are a planner for Mitchell Autonomous Agent.
Break down the following instruction into sequential steps.
Available tool namespaces: 'android.*', 'windows.system', 'windows.ui', 'vision', 'browser', 'skills.*', 'research.*'

Instruction: {task.instruction}
{skill_context}

User Profile Context:
{profile}

Available Custom Skills (from the skills log, informational):
{skills}

Output a JSON object with a 'steps' array.
Each step should have 'description', 'action' (the tool namespace needed), and optional 'depends_on' (list of 0-indexed step indices this step depends on).
"""
    messages = [{"role": "user", "content": prompt}]
    
    # Planner role: GPT-5.6 Luna (model-routing plan)
    result = await call("planner", messages=messages, task_id=task.id)
    
    # Parse output, expecting JSON block.
    try:
        content = result.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        data = json.loads(content)

        task.steps = []
        for s_data in data.get("steps", []):
            step = TaskStep(
                description=s_data.get("description", ""),
                action=s_data.get("action", None),
                depends_on=s_data.get("depends_on", []),
            )
            task.steps.append(step)

        task.save()
        return task
    except Exception as e:  # noqa: BLE001 - any planning failure is a hard error
        # Do NOT emit an unclaimable action="fallback" step. Surface it.
        raise PlanningError(
            f"Planning failed for task {task.id!r} (instruction: {task.instruction!r}): {e}"
        ) from e


async def plan_or_clarify(instruction: str, targets: list[str]) -> dict:
    from mitchell.providers.registry import cascading_call as call
    prompt = (
        f"Instruction: {instruction}\n"
        f"Targets: {targets}\n"
        "If the instruction is ambiguous, output "
        '{"status":"clarify","questions":[{"id":"...","text":"...","options":[...]}]}. '
        'Otherwise output {"status":"plan"} and a normal plan will be generated next.'
    )
    r = await call("planner", messages=[{"role": "user", "content": prompt}])
    try:
        content = r.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        data = json.loads(content)
        return data
    except Exception:
        return {"status": "plan"}
