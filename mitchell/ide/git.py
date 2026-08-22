"""Git integration engine for Mitchell Agentic IDE."""

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.ide.terminal import terminal_manager


class GitStatus(BaseModel):
    """Parsed git status state."""

    branch: str = "main"
    staged_files: List[str] = Field(default_factory=list)
    unstaged_files: List[str] = Field(default_factory=list)
    untracked_files: List[str] = Field(default_factory=list)
    is_clean: bool = True
    ahead: int = 0
    behind: int = 0


class GitManager:
    """Operations engine for Git repositories inside the IDE."""

    def __init__(self) -> None:
        self.terminal = terminal_manager

    def status(self, repo_dir: Optional[str] = None) -> GitStatus:
        """Parse status of the git working tree."""
        res = self.terminal.run_command("git status --porcelain -b", cwd=repo_dir)
        if res.exit_code != 0:
            return GitStatus(is_clean=True, branch="no_git")

        lines = res.stdout.splitlines()
        branch = "main"
        staged = []
        unstaged = []
        untracked = []

        for line in lines:
            if line.startswith("##"):
                branch = line[3:].split("...")[0].strip()
            elif len(line) >= 2:
                code = line[:2]
                file_name = line[3:].strip()
                if code == "??":
                    untracked.append(file_name)
                else:
                    if code[0] in ("M", "A", "D", "R", "C"):
                        staged.append(file_name)
                    if code[1] in ("M", "D"):
                        unstaged.append(file_name)

        is_clean = len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0
        return GitStatus(
            branch=branch,
            staged_files=staged,
            unstaged_files=unstaged,
            untracked_files=untracked,
            is_clean=is_clean,
        )

    def diff(self, repo_dir: Optional[str] = None, staged: bool = False) -> str:
        """Get git diff output."""
        flag = "--staged" if staged else ""
        res = self.terminal.run_command(f"git diff {flag}", cwd=repo_dir)
        return res.stdout

    def commit(self, message: str, repo_dir: Optional[str] = None, add_all: bool = True) -> Dict[str, Any]:
        """Stage files and create a git commit."""
        if add_all:
            self.terminal.run_command("git add -A", cwd=repo_dir)
        safe_msg = message.replace('"', '\\"')
        res = self.terminal.run_command(f'git commit -m "{safe_msg}"', cwd=repo_dir)
        return {
            "success": res.exit_code == 0,
            "output": res.stdout or res.stderr,
        }

    def log(self, repo_dir: Optional[str] = None, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent commit history."""
        res = self.terminal.run_command(f'git log -n {limit} --pretty=format:"%h|%an|%ar|%s"', cwd=repo_dir)
        commits = []
        if res.exit_code == 0 and res.stdout:
            for line in res.stdout.splitlines():
                parts = line.split("|")
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "time_ago": parts[2],
                        "message": parts[3],
                    })
        return commits


git_manager = GitManager()

__all__ = ["GitStatus", "GitManager", "git_manager"]
