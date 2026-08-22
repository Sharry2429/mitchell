"""Bridges to external coding tools and agentic platforms (Antigravity, Claude Code, Codex, OpenCode)."""

import os
import shutil
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.ide.terminal import terminal_manager


class ExternalToolStatus(BaseModel):
    """Availability status of an external coding assistant or CLI tool."""

    name: str
    installed: bool
    executable_path: Optional[str] = None
    version: Optional[str] = None
    description: str = ""


class ExternalPlatformBridges:
    """Manages detection and invocation bridges to external agentic coding platforms."""

    KNOWN_TOOLS = {
        "antigravity": {"bin": "antigravity", "desc": "Google Antigravity Agentic IDE & CLI"},
        "claude": {"bin": "claude", "desc": "Anthropic Claude Code CLI"},
        "opencode": {"bin": "opencode", "desc": "OpenCode Multi-Model Coding Agent"},
        "git": {"bin": "git", "desc": "Git Version Control System"},
        "pytest": {"bin": "pytest", "desc": "Python Test Framework"},
        "npm": {"bin": "npm", "desc": "Node Package Manager"},
        "docker": {"bin": "docker", "desc": "Docker Container Runtime"},
    }

    def scan_installed_tools(self) -> List[ExternalToolStatus]:
        """Scan system PATH for known developer tools."""
        statuses = []
        for name, info in self.KNOWN_TOOLS.items():
            exe = shutil.which(info["bin"])
            version = None
            if exe:
                # Try getting version
                try:
                    res = terminal_manager.run_command(f"{info['bin']} --version", timeout_seconds=5.0)
                    if res.exit_code == 0:
                        version = res.stdout.strip().splitlines()[0] if res.stdout.strip() else None
                except Exception:
                    pass

            statuses.append(
                ExternalToolStatus(
                    name=name,
                    installed=bool(exe),
                    executable_path=exe,
                    version=version,
                    description=info["desc"],
                )
            )
        return statuses

    def run_external_agent(self, tool_name: str, prompt_or_args: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Dispatch a task to an external CLI coding assistant."""
        exe = shutil.which(tool_name)
        if not exe:
            return {"status": "error", "message": f"Tool '{tool_name}' is not installed in system PATH"}

        cmd = f'"{exe}" {prompt_or_args}'
        res = terminal_manager.run_command(cmd, cwd=cwd, timeout_seconds=300.0)
        return {
            "status": "success" if res.exit_code == 0 else "error",
            "exit_code": res.exit_code,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "duration_s": res.duration_s,
        }


platform_bridges = ExternalPlatformBridges()

__all__ = ["ExternalToolStatus", "ExternalPlatformBridges", "platform_bridges"]
