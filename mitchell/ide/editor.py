"""Multi-file code editor engine with AST validation, diff computation, and safe refactoring tools."""

import ast
import difflib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class FileEditResult(BaseModel):
    """Result of a file modification or refactoring operation."""

    file_path: str
    success: bool
    diff: str = ""
    lines_added: int = 0
    lines_removed: int = 0
    syntax_valid: bool = True
    error_message: Optional[str] = None


class CodeEditor:
    """Operations engine for safe multi-file reading, writing, patching, and code analysis."""

    def read_file(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """Read full or partial file contents."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        if start_line is not None or end_line is not None:
            s = (start_line - 1) if start_line and start_line > 0 else 0
            e = end_line if end_line else len(lines)
            return "".join(lines[s:e])
        return "".join(lines)

    def write_file(self, file_path: str, content: str, validate_syntax: bool = True) -> FileEditResult:
        """Write content to file with optional Python syntax check and unified diff."""
        path = Path(file_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        old_content = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

        # Validate syntax for python files
        if validate_syntax and path.suffix == ".py":
            try:
                ast.parse(content, filename=str(path))
            except SyntaxError as e:
                return FileEditResult(
                    file_path=str(path),
                    success=False,
                    syntax_valid=False,
                    error_message=f"SyntaxError on line {e.lineno}: {e.msg}",
                )

        # Compute diff
        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{path.name}",
                tofile=f"b/{path.name}",
            )
        )
        diff_str = "".join(diff_lines)
        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        path.write_text(content, encoding="utf-8")

        event_log.log_event(
            "ide_file_edited",
            source="code_editor",
            data={"file": str(path), "added": added, "removed": removed},
        )
        logger.info("File edited: {} (+{}, -{})", path.name, added, removed)

        return FileEditResult(
            file_path=str(path),
            success=True,
            diff=diff_str,
            lines_added=added,
            lines_removed=removed,
            syntax_valid=True,
        )

    def replace_in_file(
        self,
        file_path: str,
        target_snippet: str,
        replacement: str,
        validate_syntax: bool = True,
    ) -> FileEditResult:
        """Perform exact surgical snippet replacement."""
        path = Path(file_path).resolve()
        if not path.exists():
            return FileEditResult(file_path=str(path), success=False, error_message="File not found")

        content = path.read_text(encoding="utf-8", errors="replace")
        if target_snippet not in content:
            return FileEditResult(
                file_path=str(path),
                success=False,
                error_message=f"Target snippet not found in {path.name}",
            )

        new_content = content.replace(target_snippet, replacement, 1)
        return self.write_file(str(path), new_content, validate_syntax=validate_syntax)

    def search_files(
        self,
        root_dir: str,
        query: str,
        file_pattern: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search text across codebase files."""
        root = Path(root_dir).resolve()
        results = []

        for r, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__")]
            for f in files:
                if file_pattern and not Path(f).match(file_pattern):
                    continue
                full_path = Path(r) / f
                try:
                    lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    for idx, line in enumerate(lines, start=1):
                        if query.lower() in line.lower():
                            results.append({
                                "file": full_path.relative_to(root).as_posix(),
                                "line_number": idx,
                                "line_content": line.strip(),
                            })
                            if len(results) >= max_results:
                                return results
                except Exception:
                    continue

        return results


code_editor = CodeEditor()

__all__ = ["FileEditResult", "CodeEditor", "code_editor"]
