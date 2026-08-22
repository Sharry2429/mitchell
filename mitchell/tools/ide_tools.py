"""IDE tools for the Mitchell ToolRegistry exposing project scaffolding, code editing, terminal commands, and testing."""

import json
from typing import Any, Dict, List, Optional

from mitchell.ide import (
    code_editor,
    code_runner,
    git_manager,
    platform_bridges,
    project_scaffolder,
    terminal_manager,
)
from mitchell.tools.registry import Tool


def tool_ide_run_command(command: str, cwd: Optional[str] = None) -> str:
    """Execute a shell command inside the IDE terminal."""
    res = terminal_manager.run_command(command=command, cwd=cwd)
    return f"Exit Code: {res.exit_code}\nOutput:\n{res.stdout}\nErrors:\n{res.stderr}"


def tool_ide_edit_file(file_path: str, content: str) -> str:
    """Write or overwrite a file in the workspace or project directory."""
    res = code_editor.write_file(file_path=file_path, content=content)
    if res.success:
        return f"File '{file_path}' written successfully (+{res.lines_added}, -{res.lines_removed} lines)."
    return f"Failed to write file: {res.error_message}"


def tool_ide_replace_in_file(file_path: str, target: str, replacement: str) -> str:
    """Replace an exact code snippet in a file."""
    res = code_editor.replace_in_file(file_path=file_path, target_snippet=target, replacement=replacement)
    if res.success:
        return f"Replaced snippet in '{file_path}' successfully."
    return f"Failed snippet replacement: {res.error_message}"


def tool_ide_git_status(repo_dir: Optional[str] = None) -> str:
    """Check git status of the project."""
    st = git_manager.status(repo_dir=repo_dir)
    return json.dumps(st.model_dump(), indent=2)


def tool_ide_run_tests(test_path: Optional[str] = None) -> str:
    """Run pytest suite in current project."""
    res = code_runner.run_tests(test_path=test_path)
    return f"Tests: {res.passed} passed, {res.failed} failed, {res.errors} errors (took {res.duration_s}s)"


# Tool instances
ide_command_tool = Tool(
    name="ide_terminal_run",
    description="Execute a shell command inside the Mitchell IDE sandbox.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "cwd": {"type": "string", "description": "Optional working directory"},
        },
        "required": ["command"],
    },
    function=tool_ide_run_command,
)

ide_edit_tool = Tool(
    name="ide_file_write",
    description="Write or overwrite a code file with automated syntax verification.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute or relative file path"},
            "content": {"type": "string", "description": "New file content"},
        },
        "required": ["file_path", "content"],
    },
    function=tool_ide_edit_file,
)

ide_replace_tool = Tool(
    name="ide_file_replace_snippet",
    description="Replace an exact code snippet in a file.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Target file path"},
            "target": {"type": "string", "description": "Exact text to find"},
            "replacement": {"type": "string", "description": "Replacement text"},
        },
        "required": ["file_path", "target", "replacement"],
    },
    function=tool_ide_replace_in_file,
)

ide_git_tool = Tool(
    name="ide_git_status",
    description="Inspect git working tree status, branches, and staged files.",
    parameters={"type": "object", "properties": {"repo_dir": {"type": "string"}}},
    function=tool_ide_git_status,
)

ide_test_tool = Tool(
    name="ide_run_tests",
    description="Run pytest suite and parse test results.",
    parameters={"type": "object", "properties": {"test_path": {"type": "string"}}},
    function=tool_ide_run_tests,
)

TOOLS = [
    ide_command_tool,
    ide_edit_tool,
    ide_replace_tool,
    ide_git_tool,
    ide_test_tool,
]
