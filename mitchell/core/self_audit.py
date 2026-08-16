import json
import os
import subprocess
import uuid
from pathlib import Path


def run_pyflakes() -> list[str]:
    try:
        result = subprocess.run(
            ["python", "-m", "pyflakes", "."], 
            capture_output=True, 
            text=True, 
            cwd=".",
            check=False
        )
        if result.returncode != 0:
            return result.stdout.splitlines() + result.stderr.splitlines()
        return []
    except Exception as e:
        return [f"Error running pyflakes: {e}"]

def run_tests() -> list[str]:
    try:
        result = subprocess.run(
            ["pytest", "tests/"], 
            capture_output=True, 
            text=True, 
            cwd=".",
            check=False
        )
        if result.returncode != 0:
            return result.stdout.splitlines() + result.stderr.splitlines()
        return []
    except Exception as e:
        return [f"Error running pytest: {e}"]

def analyze_token_usage() -> list[str]:
    p = Path(os.path.expanduser("~/.system-mcp/tokens.jsonl"))
    if not p.exists():
        return []
        
    total_tokens = 0
    count = 0
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                total_tokens += data.get("estimated_tokens", 0)
                count += 1
    except Exception:
        pass
        
    if count == 0:
        return []
        
    avg_tokens = total_tokens / count
    if avg_tokens > 2000:
        return [f"Average token usage is very high ({avg_tokens:.0f} tokens/turn). Consider lowering the history compression threshold or trimming boot.md."]
    return []

def generate_audit_tasks() -> list[dict]:
    tasks = []
    
    lint_errors = run_pyflakes()
    if lint_errors:
        task = {
            "id": str(uuid.uuid4()), 
            "instruction": "Fix the following pyflakes errors:\n" + "\n".join(lint_errors)
        }
        tasks.append(task)
        
    test_errors = run_tests()
    if test_errors:
        task = {
            "id": str(uuid.uuid4()), 
            "instruction": "Fix the following pytest failures:\n" + "\n".join(test_errors)
        }
        tasks.append(task)
        
    token_warnings = analyze_token_usage()
    if token_warnings:
        task = {
            "id": str(uuid.uuid4()), 
            "instruction": "Optimize token usage:\n" + "\n".join(token_warnings)
        }
        tasks.append(task)
        
    return tasks
