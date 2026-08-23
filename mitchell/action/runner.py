"""GitHub Actions Event Runner for Mitchell Code Action."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from mitchell.action.issue_solver import issue_solver
from mitchell.action.pr_reviewer import pr_reviewer
from mitchell.action.smart_commit import smart_commit
from mitchell.core.logging import logger


class ActionRunner:
    """Dispatches execution within GitHub Actions CI environments or local CLI."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()

    def run_from_env(self) -> Dict[str, Any]:
        """Inspect environment variables and execute appropriate action."""
        event_path = os.getenv("GITHUB_EVENT_PATH")
        event_name = os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch")
        mode = os.getenv("MITCHELL_ACTION_MODE", "auto").lower()
        prompt = os.getenv("MITCHELL_PROMPT", "")

        event_data: Dict[str, Any] = {}
        if event_path and Path(event_path).exists():
            try:
                event_data = json.loads(Path(event_path).read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed parsing GITHUB_EVENT_PATH: {}", e)

        logger.info("Mitchell Action running in mode '{}' (event: '{}')", mode, event_name)

        # 1. PR Review Mode
        if mode == "review" or event_name == "pull_request":
            report = pr_reviewer.review_diff(staged_only=False)
            md_report = pr_reviewer.format_markdown_report(report)
            print(md_report)
            return {"status": "success", "mode": "review", "verdict": report.verdict, "report": md_report}

        # 2. Issue Solver Mode
        elif mode == "solve" or (mode == "auto" and event_name in ("issues", "issue_comment")):
            issue_text = prompt
            if not issue_text and "issue" in event_data:
                issue_text = f"{event_data['issue'].get('title', '')}\n\n{event_data['issue'].get('body', '')}"
            if not issue_text and "comment" in event_data:
                issue_text = event_data["comment"].get("body", "")

            if not issue_text:
                issue_text = "Perform autonomous codebase review and health check."

            res = issue_solver.solve_issue(issue_text=issue_text)
            return {"status": "success", "mode": "solve", "result": res.model_dump()}

        # 3. Smart Commit Mode
        elif mode == "commit":
            res = smart_commit.create_commit(auto_stage=True, auto_push=False)
            return {"status": "success" if res.get("success") else "failed", "mode": "commit", "result": res}

        # Default fallback: Review
        report = pr_reviewer.review_diff()
        md_report = pr_reviewer.format_markdown_report(report)
        print(md_report)
        return {"status": "success", "mode": "review_default", "verdict": report.verdict}


action_runner = ActionRunner()

__all__ = ["ActionRunner", "action_runner"]
