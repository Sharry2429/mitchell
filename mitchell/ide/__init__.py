"""Mitchell Agentic IDE Subsystem — Project Management, File Editing, Terminal, Git, Runner, and External Bridges."""

from mitchell.ide.editor import CodeEditor, FileEditResult, code_editor
from mitchell.ide.git import GitManager, GitStatus, git_manager
from mitchell.ide.integrations import ExternalPlatformBridges, ExternalToolStatus, platform_bridges
from mitchell.ide.project import ProjectManifest, ProjectScaffolder, project_scaffolder
from mitchell.ide.runner import CodeRunner, TestRunResult, code_runner
from mitchell.ide.terminal import CommandResult, TerminalManager, terminal_manager

__all__ = [
    "ProjectScaffolder",
    "project_scaffolder",
    "ProjectManifest",
    "CodeEditor",
    "code_editor",
    "FileEditResult",
    "TerminalManager",
    "terminal_manager",
    "CommandResult",
    "GitManager",
    "git_manager",
    "GitStatus",
    "CodeRunner",
    "code_runner",
    "TestRunResult",
    "ExternalPlatformBridges",
    "platform_bridges",
    "ExternalToolStatus",
]
