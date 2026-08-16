import time
from pathlib import Path
from mitchell.core.tasks import Task, TaskState, TaskStep

class TaskLock:
    def __init__(self, task_id: str):
        self.lock_dir = Path(f"~/.system-mcp/tasks/{task_id}.lock_dir").expanduser()
        
    def __enter__(self):
        self.lock_dir.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.lock_dir.mkdir()
                break
            except FileExistsError:
                time.sleep(0.1)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.lock_dir.rmdir()
        except OSError:
            pass

class DeviceLock:
    def __init__(self):
        self.lock_dir = Path("~/.system-mcp/device.lock_dir").expanduser()
        
    def __enter__(self):
        self.lock_dir.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.lock_dir.mkdir()
                break
            except FileExistsError:
                time.sleep(0.1)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.lock_dir.rmdir()
        except OSError:
            pass

def claim_next_step(task_id: str, worker_id: str, worker_role: str) -> tuple[int, TaskStep] | tuple[None, None]:
    with TaskLock(task_id):
        task = Task.load(task_id)
        if not task:
            return None, None
            
        for i, step in enumerate(task.steps):
            if step.state == TaskState.PENDING and step.claimed_by is None:
                # Check dependencies
                deps_met = all(task.steps[d].state == TaskState.COMPLETED for d in step.depends_on)
                if deps_met:
                    action = step.action or ""
                    can_claim = False
                    
                    if worker_role == "worker-research" and ("research" in action or "browser" in action):
                        can_claim = True
                    elif worker_role == "worker-coder" and ("windows.system" in action or "skills" in action):
                        can_claim = True
                    elif worker_role == "worker-operator" and ("android" in action or "windows.ui" in action or "vision" in action):
                        can_claim = True
                    elif worker_role == "worker-general":
                        # General can claim anything if no specialist is available (simplified logic)
                        can_claim = True
                        
                    if can_claim:
                        step.claimed_by = worker_id
                        step.claimed_at = time.time()
                        step.state = TaskState.RUNNING
                        task.save()
                        return i, step
        return None, None

def mark_step_completed(task_id: str, step_index: int, verification_passed: bool | None = None):
    with TaskLock(task_id):
        task = Task.load(task_id)
        if task and 0 <= step_index < len(task.steps):
            task.steps[step_index].state = TaskState.COMPLETED
            if verification_passed is not None:
                task.steps[step_index].verification_passed = verification_passed
            task.save()

def mark_step_failed(task_id: str, step_index: int, error: str):
    with TaskLock(task_id):
        task = Task.load(task_id)
        if task and 0 <= step_index < len(task.steps):
            task.steps[step_index].state = TaskState.FAILED
            task.steps[step_index].error = error
            task.save()
