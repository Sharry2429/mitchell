"""Git Merge Conflict Resolver for Mitchell Code Action."""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from mitchell.core.logging import logger


class ConflictBlock(BaseModel):
    """Parsed merge conflict chunk in a file."""

    file_path: str
    start_line: int
    current_branch_content: str
    incoming_branch_content: str
    resolved_content: Optional[str] = None


class ConflictResolver:
    """Detects and resolves git merge conflict markers in source files."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()

    def find_conflicted_files(self) -> List[Path]:
        """Scan repository files for git conflict markers."""
        conflicted: List[Path] = []
        for path in self.root_dir.rglob("*"):
            if not path.is_file() or ".git" in path.parts or ".mitchell" in path.parts:
                continue
            if path.suffix.lower() in [".py", ".md", ".json", ".js", ".html", ".css", ".yml", ".yaml", ".txt"]:
                try:
                    content = path.read_text(encoding="utf-8")
                    if "<<<<<<<" in content and "=======" in content and ">>>>>>>" in content:
                        conflicted.append(path)
                except Exception:
                    pass
        return conflicted

    def parse_conflicts_in_text(self, text: str, file_path: str = "") -> List[ConflictBlock]:
        """Extract individual conflict blocks from text."""
        pattern = re.compile(
            r"<<<<<<<[^\n]*\n([\s\S]*?)=======\n([\s\S]*?)>>>>>>>[^\n]*\n",
            re.MULTILINE,
        )
        blocks = []
        for m in pattern.finditer(text):
            current_branch = m.group(1)
            incoming_branch = m.group(2)
            blocks.append(
                ConflictBlock(
                    file_path=file_path,
                    start_line=text[:m.start()].count("\n") + 1,
                    current_branch_content=current_branch,
                    incoming_branch_content=incoming_branch,
                )
            )
        return blocks

    def resolve_text_conflicts(self, text: str, file_path: str = "") -> Tuple[str, int]:
        """Resolve all conflict blocks in a text string and return cleaned content."""
        pattern = re.compile(
            r"<<<<<<<[^\n]*\n([\s\S]*?)=======\n([\s\S]*?)>>>>>>>[^\n]*(?:\n|$)",
            re.MULTILINE,
        )

        resolved_count = 0

        def _replacer(match: re.Match) -> str:
            nonlocal resolved_count
            resolved_count += 1
            current = match.group(1)
            incoming = match.group(2)

            # Heuristic 1: If one is empty, keep the other
            if not current.strip():
                return incoming
            if not incoming.strip():
                return current

            # Heuristic 2: If both are distinct imports or definitions, combine cleanly
            if file_path.endswith(".py"):
                combined = current + "\n" + incoming
                try:
                    ast.parse(combined)
                    return combined
                except SyntaxError:
                    pass

            # Default: combine non-duplicate lines
            curr_lines = current.splitlines()
            inc_lines = incoming.splitlines()
            combined_lines = list(curr_lines)
            for l in inc_lines:
                if l not in combined_lines:
                    combined_lines.append(l)
            return "\n".join(combined_lines) + "\n"

        cleaned = pattern.sub(_replacer, text)
        return cleaned, resolved_count

    def resolve_all_conflicts(self) -> Dict[str, Any]:
        """Scan repository, resolve all conflict markers, and save updated files."""
        conflicted_files = self.find_conflicted_files()
        if not conflicted_files:
            return {"status": "clean", "message": "No merge conflict markers detected in repository."}

        results = []
        for file_path in conflicted_files:
            try:
                original = file_path.read_text(encoding="utf-8")
                resolved, count = self.resolve_text_conflicts(original, file_path=str(file_path))
                if count > 0:
                    file_path.write_text(resolved, encoding="utf-8")
                    results.append({
                        "file": str(file_path.relative_to(self.root_dir)),
                        "conflicts_resolved": count,
                    })
            except Exception as e:
                logger.error("Failed resolving conflict in {}: {}", file_path, e)

        return {
            "status": "resolved",
            "total_files_resolved": len(results),
            "details": results,
        }


conflict_resolver = ConflictResolver()

__all__ = ["ConflictBlock", "ConflictResolver", "conflict_resolver"]
