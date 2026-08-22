"""Codebase introspection module for Mitchell's self-evolution subsystem."""

import ast
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.logging import logger
from mitchell.tools.registry import tool_registry


class CodeInspector:
    """Inspects Mitchell's own codebase, modules, classes, and registered tools."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path(__file__).resolve().parent.parent.parent

    def list_python_files(self, relative_to_pkg: str = "mitchell") -> List[Path]:
        """Find all Python source files in the specified package directory."""
        target_dir = self.root_dir / relative_to_pkg
        if not target_dir.exists():
            return []
        return sorted([p for p in target_dir.rglob("*.py") if "__pycache__" not in p.parts])

    def inspect_file_ast(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Python source file and extract classes, functions, and docstrings."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except Exception as e:
            logger.error("Failed to parse AST for {}: {}", file_path, e)
            return {"error": str(e), "file": str(file_path)}

        classes: List[Dict[str, Any]] = []
        functions: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    "name": node.name,
                    "docstring": ast.get_docstring(node) or "",
                    "methods": methods,
                    "lineno": node.lineno,
                })
            elif isinstance(node, ast.FunctionDef):
                # Top level functions
                if isinstance(getattr(node, "parent", None), ast.ClassDef):
                    continue
                args = [a.arg for a in node.args.args]
                functions.append({
                    "name": node.name,
                    "docstring": ast.get_docstring(node) or "",
                    "args": args,
                    "lineno": node.lineno,
                })

        return {
            "file": str(file_path.relative_to(self.root_dir)),
            "classes": classes,
            "functions": functions,
            "line_count": len(content.splitlines()),
        }

    def inspect_registered_tools(self) -> List[Dict[str, Any]]:
        """Get structured overview of all currently registered Mitchell tools."""
        tools = tool_registry.get_all()
        result = []
        for name, t in tools.items():
            result.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "is_dangerous": getattr(t, "is_dangerous", False),
            })
        return result

    def get_system_summary(self) -> Dict[str, Any]:
        """Generate a high-level architectural summary of the local Mitchell system."""
        py_files = self.list_python_files("mitchell")
        test_files = self.list_python_files("tests")
        tools = self.inspect_registered_tools()

        return {
            "total_source_files": len(py_files),
            "total_test_files": len(test_files),
            "total_registered_tools": len(tools),
            "tools": tools,
            "packages": sorted(list({p.parent.relative_to(self.root_dir).as_posix() for p in py_files})),
        }


code_inspector = CodeInspector()

__all__ = ["CodeInspector", "code_inspector"]
