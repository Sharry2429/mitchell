"""Build, run, and test execution engine for Mitchell Agentic IDE."""

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.ide.terminal import CommandResult, terminal_manager


class TestRunResult(BaseModel):
    """Parsed result of an automated test run."""

    framework: str = "pytest"
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_s: float = 0.0
    raw_output: str = ""
    success: bool = True


class CodeRunner:
    """Operations engine for executing, building, and testing projects inside the IDE."""

    def __init__(self) -> None:
        self.terminal = terminal_manager

    def run_python_file(self, file_path: str, cwd: Optional[str] = None) -> CommandResult:
        """Run a Python script."""
        import sys
        python_exe = sys.executable
        return self.terminal.run_command(f'"{python_exe}" "{file_path}"', cwd=cwd)

    def run_tests(self, cwd: Optional[str] = None, test_path: Optional[str] = None) -> TestRunResult:
        """Run pytest suite and parse passed/failed summary."""
        import sys
        python_exe = sys.executable
        cmd = f'"{python_exe}" -m pytest {test_path or ""} -v --tb=short'
        res = self.terminal.run_command(cmd, cwd=cwd, timeout_seconds=120.0)

        passed = 0
        failed = 0
        errors = 0

        # Parse pytest output
        for line in res.stdout.splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                parts = line.split(",")
                for p in parts:
                    p = p.strip()
                    if "passed" in p:
                        try: passed = int(p.split()[0])
                        except Exception: pass
                    elif "failed" in p:
                        try: failed = int(p.split()[0])
                        except Exception: pass
                    elif "error" in p:
                        try: errors = int(p.split()[0])
                        except Exception: pass

        return TestRunResult(
            passed=passed,
            failed=failed,
            errors=errors,
            duration_s=res.duration_s,
            raw_output=res.stdout + "\n" + res.stderr,
            success=res.exit_code == 0,
        )


code_runner = CodeRunner()

__all__ = ["TestRunResult", "CodeRunner", "code_runner"]
