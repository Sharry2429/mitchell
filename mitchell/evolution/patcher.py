"""Self-patching and bug diagnostic engine for Mitchell's self-evolution subsystem."""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class SelfPatcher:
    """Diagnoses runtime errors and safely applies surgical patches with rollback capability."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path(__file__).resolve().parent.parent.parent
        self.backups: Dict[str, str] = {}

    def backup_file(self, target_path: Path) -> None:
        """Store original content in memory before applying patch."""
        if target_path.exists():
            self.backups[str(target_path)] = target_path.read_text(encoding="utf-8")

    def rollback(self, target_path: Path) -> bool:
        """Rollback a modified file to its previous state."""
        key = str(target_path)
        if key in self.backups:
            target_path.write_text(self.backups[key], encoding="utf-8")
            logger.info("Rolled back {} to original state.", target_path)
            return True
        return False

    def diagnose_traceback(self, error_trace: str) -> Dict[str, Any]:
        """Analyze a Python traceback to find the offending file and line number."""
        lines = error_trace.strip().splitlines()
        candidate_file = None
        candidate_line = None

        for line in reversed(lines):
            if 'File "' in line and ", line " in line:
                parts = line.split('File "')[1].split('", line ')
                file_str = parts[0]
                line_str = parts[1].split(",")[0]
                if "mitchell" in file_str:
                    candidate_file = file_str
                    try:
                        candidate_line = int(line_str)
                    except ValueError:
                        pass
                    break

        return {
            "candidate_file": candidate_file,
            "candidate_line": candidate_line,
            "error_type": lines[-1] if lines else "UnknownError",
        }

    def apply_patch(
        self,
        target_file: Path,
        old_snippet: str,
        new_snippet: str,
    ) -> Dict[str, Any]:
        """Apply a replacement patch to a target file after backup and syntax check."""
        if not target_file.exists():
            return {"status": "error", "error": f"File does not exist: {target_file}"}

        content = target_file.read_text(encoding="utf-8")
        if old_snippet not in content:
            return {"status": "error", "error": "Target snippet to replace not found in file."}

        # Backup first
        self.backup_file(target_file)

        patched_content = content.replace(old_snippet, new_snippet, 1)

        # Validate syntax of patched file
        try:
            ast.parse(patched_content)
        except SyntaxError as e:
            logger.error("Patch resulted in SyntaxError at line {}: {}", e.lineno, e.msg)
            return {"status": "error", "error": f"Patch introduced SyntaxError: {e}"}

        # Write patched file
        target_file.write_text(patched_content, encoding="utf-8")

        event_log.log_event(
            "self_patch_applied",
            source="self_patcher",
            data={"file": str(target_file)},
        )

        logger.info("Successfully applied self-patch to {}", target_file)
        return {
            "status": "success",
            "file": str(target_file),
            "message": "Patch applied successfully.",
        }


self_patcher = SelfPatcher()

__all__ = ["SelfPatcher", "self_patcher"]
