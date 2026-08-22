"""Interactive terminal session manager for executing commands inside the Mitchell Agentic IDE."""

import asyncio
import os
import subprocess
import sys
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class CommandResult(BaseModel):
    """Result of an executed terminal command."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    cwd: str


class TerminalManager:
    """Manages terminal processes and command executions."""

    def __init__(self) -> None:
        self.default_shell = "powershell.exe" if sys.platform == "win32" else "/bin/bash"

    def run_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout_seconds: float = 60.0,
    ) -> CommandResult:
        """Run a command synchronously and capture stdout, stderr, and exit code."""
        start = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        import time
        start_time = time.time()
        work_dir = cwd or os.getcwd()

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = -1
            stderr += "\n[Error: Command timed out]"
        except Exception as e:
            stdout = ""
            stderr = str(e)
            exit_code = 1

        duration = round(time.time() - start_time, 2)

        event_log.log_event(
            "ide_command_executed",
            source="terminal_manager",
            data={"cmd": command, "code": exit_code, "duration_s": duration},
        )
        logger.info("IDE Command executed: '{}' (exit: {}, {}s)", command, exit_code, duration)

        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_s=duration,
            cwd=work_dir,
        )


terminal_manager = TerminalManager()

__all__ = ["CommandResult", "TerminalManager", "terminal_manager"]
