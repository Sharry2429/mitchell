"""Autonomous Git Action tools registered into Mitchell ToolRegistry."""

import json
from pathlib import Path
from typing import Optional

from mitchell.action.conflict_resolver import conflict_resolver
from mitchell.action.issue_solver import issue_solver
from mitchell.action.pr_reviewer import pr_reviewer
from mitchell.action.smart_commit import smart_commit
from mitchell.action.workflow_generator import workflow_generator
from mitchell.tools.registry import Tool


def tool_git_action_review(base_branch: str = "HEAD", staged_only: bool = False) -> str:
    """Generate structured markdown code review on git diff."""
    report = pr_reviewer.review_diff(base=base_branch, staged_only=staged_only)
    md = pr_reviewer.format_markdown_report(report)
    return json.dumps({
        "verdict": report.verdict,
        "files_changed": report.files_changed,
        "insertions": report.insertions,
        "deletions": report.deletions,
        "findings_count": len(report.findings),
        "markdown_report": md,
    }, indent=2)


def tool_git_action_smart_commit(headline: Optional[str] = None, auto_push: bool = False) -> str:
    """Auto-stage changes, generate semantic conventional commit message, and commit."""
    res = smart_commit.create_commit(headline=headline, auto_stage=True, auto_push=auto_push)
    return json.dumps(res, indent=2)


def tool_git_action_solve_issue(issue_text: str, branch_name: Optional[str] = None) -> str:
    """End-to-end issue solver creating a feature branch, running tests, and preparing commits."""
    res = issue_solver.solve_issue(issue_text=issue_text, branch_name=branch_name)
    return res.model_dump_json(indent=2)


def tool_git_action_resolve_conflicts() -> str:
    """Scan repository for conflict markers (<<<<<<< HEAD, =======, >>>>>>>) and reconcile code."""
    res = conflict_resolver.resolve_all_conflicts()
    return json.dumps(res, indent=2)


def tool_git_action_generate_workflow(target_dir: Optional[str] = None) -> str:
    """Scaffold action.yml and .github/workflows/mitchell-code-action.yml."""
    gen = workflow_generator if not target_dir else workflow_generator.__class__(root_dir=Path(target_dir))
    paths = gen.scaffold_all()
    return json.dumps({
        "status": "success",
        "generated_files": paths,
    }, indent=2)


git_action_review_tool = Tool(
    name="git_action_review",
    description="Perform deep autonomous code review on git working tree diff or pull request.",
    parameters={
        "type": "object",
        "properties": {
            "base_branch": {"type": "string", "description": "Base branch or commit hash to diff against (default: 'HEAD')"},
            "staged_only": {"type": "boolean", "description": "Whether to review staged changes only"},
        },
    },
    function=tool_git_action_review,
)

git_action_smart_commit_tool = Tool(
    name="git_action_smart_commit",
    description="Analyze git working tree diff, generate semantic conventional commit, stage and commit.",
    parameters={
        "type": "object",
        "properties": {
            "headline": {"type": "string", "description": "Optional override headline commit message"},
            "auto_push": {"type": "boolean", "description": "Whether to automatically push to remote origin branch"},
        },
    },
    function=tool_git_action_smart_commit,
)

git_action_solve_issue_tool = Tool(
    name="git_action_solve_issue",
    description="Autonomously implement a requested issue or feature, run tests, and create a git commit.",
    parameters={
        "type": "object",
        "properties": {
            "issue_text": {"type": "string", "description": "Issue title and description or feature requirement prompt"},
            "branch_name": {"type": "string", "description": "Optional target git branch name to create"},
        },
        "required": ["issue_text"],
    },
    function=tool_git_action_solve_issue,
)

git_action_resolve_conflicts_tool = Tool(
    name="git_action_resolve_conflicts",
    description="Detect and automatically reconcile git merge conflict markers across repository files.",
    parameters={"type": "object", "properties": {}},
    function=tool_git_action_resolve_conflicts,
)

git_action_generate_workflow_tool = Tool(
    name="git_action_generate_workflow",
    description="Generate official action.yml and GitHub Actions CI workflow for Mitchell Code Action.",
    parameters={
        "type": "object",
        "properties": {
            "target_dir": {"type": "string", "description": "Optional target workspace root directory"},
        },
    },
    function=tool_git_action_generate_workflow,
)

TOOLS = [
    git_action_review_tool,
    git_action_smart_commit_tool,
    git_action_solve_issue_tool,
    git_action_resolve_conflicts_tool,
    git_action_generate_workflow_tool,
]

__all__ = [
    "TOOLS",
    "tool_git_action_review",
    "tool_git_action_smart_commit",
    "tool_git_action_solve_issue",
    "tool_git_action_resolve_conflicts",
    "tool_git_action_generate_workflow",
    "git_action_review_tool",
    "git_action_smart_commit_tool",
    "git_action_solve_issue_tool",
    "git_action_resolve_conflicts_tool",
    "git_action_generate_workflow_tool",
]
