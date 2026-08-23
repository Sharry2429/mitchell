"""Autonomous Issue-to-PR Solver for Mitchell Code Action."""

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from mitchell.action.smart_commit import smart_commit
from mitchell.core.logging import logger
from mitchell.manager import Manager


class IssueSolutionResult(BaseModel):
    """Result of autonomous issue resolution."""

    issue_title: str
    branch_name: str
    success: bool
    test_verified: bool
    commit_created: bool
    commit_message: Optional[str] = None
    files_changed: list[str] = Field(default_factory=list)
    summary: str


class IssueSolver:
    """Solves GitHub Issues or tasks autonomously, tests code, and prepares commits."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()
        self.manager = Manager()

    def solve_issue(
        self,
        issue_text: str,
        branch_name: Optional[str] = None,
        run_tests: bool = True,
        auto_commit: bool = True,
    ) -> IssueSolutionResult:
        """Execute full issue resolution workflow on repository."""
        # 1. Create or switch to feature branch
        clean_title = "".join(c if c.isalnum() else "-" for c in issue_text[:30].strip().lower()).strip("-")
        target_branch = branch_name or f"mitchell/fix-{clean_title}"

        try:
            subprocess.run(["git", "checkout", "-b", target_branch], cwd=str(self.root_dir), capture_output=True)
        except Exception:
            pass

        # 2. Dispatch task goal through Mitchell Manager
        prompt = f"Resolve this issue with high precision and Karpathy principles: {issue_text}"
        manager_response = self.manager.receive(prompt)

        # 3. Check modified files
        files, diff = smart_commit.get_status_and_diff()

        # 4. Verify with test runner
        test_passed = True
        if run_tests:
            try:
                test_res = subprocess.run(["pytest", "-q"], cwd=str(self.root_dir), capture_output=True, text=True)
                test_passed = (test_res.returncode == 0)
            except Exception:
                test_passed = False

        # 5. Commit if requested
        commit_created = False
        commit_msg = None
        if auto_commit and files:
            res_commit = smart_commit.create_commit(auto_stage=True, auto_push=False)
            if res_commit.get("success"):
                commit_created = True
                commit_msg = res_commit.get("commit_message")

        return IssueSolutionResult(
            issue_title=issue_text[:60],
            branch_name=target_branch,
            success=test_passed and (bool(files) or commit_created),
            test_verified=test_passed,
            commit_created=commit_created,
            commit_message=commit_msg,
            files_changed=files,
            summary=f"Resolved issue '{issue_text[:60]}' on branch '{target_branch}'. Tests passed: {test_passed}. Committed: {commit_created}.",
        )


issue_solver = IssueSolver()

__all__ = ["IssueSolutionResult", "IssueSolver", "issue_solver"]
