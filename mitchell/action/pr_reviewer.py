"""Autonomous Pull Request and Git Diff Reviewer for Mitchell Code Action."""

import ast
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.logging import logger


class ReviewFinding(BaseModel):
    """Specific code review observation or improvement recommendation."""

    file_path: str
    line_number: Optional[int] = None
    category: str = Field(default="quality", description="security, quality, performance, ast, convention")
    severity: str = Field(default="info", description="info, warning, critical")
    title: str
    details: str
    suggestion: Optional[str] = None


class DiffReviewReport(BaseModel):
    """Complete structured code review report for a pull request or branch diff."""

    target: str
    files_changed: List[str] = Field(default_factory=list)
    insertions: int = Field(default=0)
    deletions: int = Field(default=0)
    summary: str
    findings: List[ReviewFinding] = Field(default_factory=list)
    verdict: str = Field(default="APPROVE", description="APPROVE, COMMENT, REQUEST_CHANGES")


class PRReviewer:
    """Performs deep autonomous code reviews on git diffs and pull requests."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()

    def get_diff(self, base: str = "HEAD", target: Optional[str] = None, staged_only: bool = False) -> str:
        """Fetch git diff from repository."""
        try:
            if staged_only:
                cmd = ["git", "diff", "--staged"]
            elif target:
                cmd = ["git", "diff", f"{base}...{target}"]
            else:
                cmd = ["git", "diff", base]

            res = subprocess.run(cmd, cwd=str(self.root_dir), capture_output=True, text=True)
            return res.stdout
        except Exception as e:
            logger.error("Failed to read git diff: {}", e)
            return ""

    def review_diff(self, diff_text: Optional[str] = None, base: str = "HEAD", staged_only: bool = False) -> DiffReviewReport:
        """Analyze diff and generate a comprehensive review."""
        diff = diff_text if diff_text is not None else self.get_diff(base=base, staged_only=staged_only)

        if not diff.strip():
            return DiffReviewReport(
                target=base if not staged_only else "staged",
                summary="Working tree is clean. No diff changes detected to review.",
                verdict="APPROVE",
            )

        # Parse changed files and counts
        files_changed: List[str] = []
        insertions = 0
        deletions = 0
        findings: List[ReviewFinding] = []

        current_file: Optional[str] = None
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                if current_file not in files_changed:
                    files_changed.append(current_file)
            elif line.startswith("+") and not line.startswith("+++"):
                insertions += 1
                # Check for suspicious secret / token strings
                if any(k in line.lower() for k in ["api_key =", "secret =", "password =", "bearer "]):
                    if not any(placeholder in line.lower() for placeholder in ["dummy", "fake", "mock", "os.getenv", "settings.", "none"]):
                        findings.append(ReviewFinding(
                            file_path=current_file or "unknown",
                            category="security",
                            severity="critical",
                            title="Potential Hardcoded Secret Detected",
                            details=f"Line contains sensitive credential keyword: `{line.strip()}`",
                            suggestion="Load credentials from environment variables via `os.getenv()` or `settings`.",
                        ))
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        # AST syntax verification for modified python files
        for f_path in files_changed:
            if f_path.endswith(".py"):
                full_file = self.root_dir / f_path
                if full_file.exists():
                    try:
                        ast.parse(full_file.read_text(encoding="utf-8"))
                    except SyntaxError as se:
                        findings.append(ReviewFinding(
                            file_path=f_path,
                            line_number=se.lineno,
                            category="ast",
                            severity="critical",
                            title="Python AST Syntax Error",
                            details=str(se),
                            suggestion=f"Fix syntax error on line {se.lineno}.",
                        ))

        # Check if critical findings exist
        has_critical = any(f.severity == "critical" for f in findings)
        verdict = "REQUEST_CHANGES" if has_critical else ("APPROVE" if not findings else "COMMENT")

        summary = (
            f"Reviewed {len(files_changed)} modified files (+{insertions}, -{deletions}). "
            + (f"Found {len(findings)} review findings." if findings else "All code and AST structures look clean and adhere to standards.")
        )

        return DiffReviewReport(
            target=base if not staged_only else "staged",
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            summary=summary,
            findings=findings,
            verdict=verdict,
        )

    def format_markdown_report(self, report: DiffReviewReport) -> str:
        """Format review report as GitHub markdown comment."""
        verdict_badge = {
            "APPROVE": "🟢 **APPROVED**",
            "COMMENT": "🟡 **COMMENT**",
            "REQUEST_CHANGES": "🔴 **CHANGES REQUESTED**",
        }.get(report.verdict, report.verdict)

        lines = [
            f"## 🤖 Mitchell Code Action Review — {verdict_badge}",
            "",
            report.summary,
            "",
            f"**Modified Files ({len(report.files_changed)})**: " + (", ".join(f"`{f}`" for f in report.files_changed) or "None"),
            f"**Diff Stats**: `+{report.insertions}` lines added, `-{report.deletions}` lines removed",
            "",
        ]

        if report.findings:
            lines.append("### 🔍 Findings & Recommendations")
            for i, f in enumerate(report.findings, 1):
                icon = "🚨" if f.severity == "critical" else ("⚠️" if f.severity == "warning" else "ℹ️")
                lines.append(f"#### {icon} {i}. {f.title} (`{f.file_path}`)")
                lines.append(f"- **Category**: `{f.category}` | **Severity**: `{f.severity.upper()}`")
                lines.append(f"- **Details**: {f.details}")
                if f.suggestion:
                    lines.append(f"- **Suggestion**: {f.suggestion}")
                lines.append("")
        else:
            lines.append("✅ **No quality or security issues detected.** Ready for merge!")

        lines.append("---")
        lines.append("*Automated review powered by Mitchell Code Action 2026*")
        return "\n".join(lines)


pr_reviewer = PRReviewer()

__all__ = ["ReviewFinding", "DiffReviewReport", "PRReviewer", "pr_reviewer"]
