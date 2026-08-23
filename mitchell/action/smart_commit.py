"""Semantic Conventional Commit Generator for Mitchell Code Action."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from mitchell.core.logging import logger


class CommitProposal(BaseModel):
    """Structured conventional commit proposal."""

    type: str = Field(default="feat", description="feat, fix, refactor, test, docs, chore, perf, ci")
    scope: Optional[str] = Field(default=None, description="Component or package scope")
    headline: str = Field(..., description="Short semantic summary")
    description: Optional[str] = Field(default=None, description="Detailed body description")
    files_changed: List[str] = Field(default_factory=list)


class SmartCommitEngine:
    """Analyzes git working tree and synthesizes semantic conventional commits."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()

    def get_status_and_diff(self) -> Tuple[List[str], str]:
        """Fetch git status short summary and unified diff."""
        try:
            st = subprocess.run(["git", "status", "-s"], cwd=str(self.root_dir), capture_output=True, text=True)
            files = [line.strip().split()[-1] for line in st.stdout.splitlines() if line.strip()]

            diff = subprocess.run(["git", "diff", "HEAD"], cwd=str(self.root_dir), capture_output=True, text=True)
            return files, diff.stdout
        except Exception as e:
            logger.error("Git status failed: {}", e)
            return [], ""

    def analyze_commit(self, files: Optional[List[str]] = None, diff_text: Optional[str] = None) -> CommitProposal:
        """Determine conventional commit type, scope, and headline from modified files and diff."""
        if files is None or diff_text is None:
            files, diff_text = self.get_status_and_diff()

        if not files:
            return CommitProposal(
                type="chore",
                headline="chore: update working tree (no modified files detected)",
                files_changed=[],
            )

        # Analyze file types and directories
        is_test = all("test" in f.lower() for f in files)
        is_docs = all(f.lower().endswith(".md") or "docs" in f.lower() for f in files)
        is_ci = all(".github" in f.lower() or "workflow" in f.lower() for f in files)
        has_tests = any("test" in f.lower() for f in files)

        # Determine type
        c_type = "feat"
        if is_test:
            c_type = "test"
        elif is_docs:
            c_type = "docs"
        elif is_ci:
            c_type = "ci"
        elif "fix" in diff_text.lower() or "bug" in diff_text.lower() or "error" in diff_text.lower():
            c_type = "fix"
        elif "refactor" in diff_text.lower() or "cleanup" in diff_text.lower():
            c_type = "refactor"

        # Determine scope
        scope = None
        if any("action" in f.lower() for f in files):
            scope = "action"
        elif any("plugin" in f.lower() for f in files):
            scope = "plugins"
        elif any("skill" in f.lower() for f in files):
            scope = "skills"
        elif any("mcp" in f.lower() for f in files):
            scope = "mcp"
        elif any("studio" in f.lower() for f in files):
            scope = "studio"
        elif any("cli" in f.lower() for f in files):
            scope = "cli"

        scope_str = f"({scope})" if scope else ""
        sample_names = ", ".join(Path(f).stem for f in files[:3])
        if len(files) > 3:
            sample_names += f" and {len(files) - 3} other files"

        headline = f"{c_type}{scope_str}: update {sample_names}"
        if c_type == "test":
            headline = f"test{scope_str}: add test verification coverage for {sample_names}"
        elif c_type == "docs":
            headline = f"docs{scope_str}: update documentation for {sample_names}"

        return CommitProposal(
            type=c_type,
            scope=scope,
            headline=headline,
            description=f"Automated semantic commit for changes in {len(files)} files:\n" + "\n".join(f"- {f}" for f in files),
            files_changed=files,
        )

    def create_commit(
        self,
        headline: Optional[str] = None,
        auto_stage: bool = True,
        auto_push: bool = False,
    ) -> Dict[str, Any]:
        """Auto-stage changes, craft conventional message, commit, and optionally push."""
        files, diff = self.get_status_and_diff()
        if not files:
            return {"success": False, "message": "Nothing to commit, working tree is clean."}

        proposal = self.analyze_commit(files=files, diff_text=diff)
        commit_msg = headline or proposal.headline

        try:
            if auto_stage:
                subprocess.run(["git", "add", "."], cwd=str(self.root_dir), check=True)

            res = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                check=True,
            )

            pushed = False
            if auto_push:
                subprocess.run(["git", "push", "origin", "HEAD"], cwd=str(self.root_dir), check=True)
                pushed = True

            logger.info("SmartCommit: Created commit '{}'", commit_msg)
            return {
                "success": True,
                "commit_message": commit_msg,
                "files_committed": files,
                "pushed": pushed,
                "stdout": res.stdout,
            }
        except Exception as e:
            logger.error("SmartCommit failed: {}", e)
            return {"success": False, "error": str(e)}


smart_commit = SmartCommitEngine()

__all__ = ["CommitProposal", "SmartCommitEngine", "smart_commit"]
