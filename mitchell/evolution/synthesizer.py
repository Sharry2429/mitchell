"""Automated tool and skill synthesizer for Mitchell's self-evolution subsystem."""

import ast
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.tools.registry import Tool, tool_registry


class ToolSynthesizer:
    """Synthesizes, registers, and persists new Mitchell tools and agent skills."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path(__file__).resolve().parent.parent.parent
        self.dynamic_tools_dir = self.root_dir / "mitchell" / "tools" / "dynamic"
        self.dynamic_tools_dir.mkdir(parents=True, exist_ok=True)
        # Create __init__.py in dynamic tools dir if missing
        init_file = self.dynamic_tools_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Dynamically synthesized Mitchell tools."""\n', encoding="utf-8")

    def validate_python_code(self, code_str: str) -> Tuple[bool, Optional[str]]:
        """Check if generated code has valid Python syntax."""
        try:
            ast.parse(code_str)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

    def check_safety_invariants(self, code_str: str) -> Tuple[bool, Optional[str]]:
        """Enforce strict safety rules: no os.system destructive commands, no credential exfiltration."""
        forbidden_patterns = [
            "rm -rf",
            "format c:",
            "shutil.rmtree('/')",
            "shutil.rmtree('C:\\\\')",
            "os.environ.clear()",
        ]
        for pattern in forbidden_patterns:
            if pattern in code_str:
                return False, f"Safety invariant violation: prohibited string '{pattern}' detected."
        return True, None

    def synthesize_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function_code: str,
        test_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesize a new Python tool, validate safety, compile, and register into ToolRegistry."""
        # 1. Validate Syntax
        is_valid, error = self.validate_python_code(function_code)
        if not is_valid:
            logger.error("Synthesizer syntax validation failed: {}", error)
            return {"status": "error", "error": error}

        # 2. Check Safety Invariants
        safe, safety_err = self.check_safety_invariants(function_code)
        if not safe:
            logger.warning("Synthesizer safety gate blocked tool generation: {}", safety_err)
            return {"status": "error", "error": safety_err}

        # 3. Dynamic Execution & Tool Registration
        namespace: Dict[str, Any] = {}
        try:
            exec(function_code, namespace)  # nosec
        except Exception as e:
            logger.error("Failed to compile synthesized function: {}", e)
            return {"status": "error", "error": f"Execution error: {e}"}

        # Find target callable
        target_fn = None
        for k, v in namespace.items():
            if callable(v) and not k.startswith("__"):
                target_fn = v
                break

        if target_fn is None:
            return {"status": "error", "error": "No callable function found in provided code."}

        new_tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=target_fn,
        )
        tool_registry.register(new_tool)

        # 4. Persist to dynamic tools directory
        tool_file = self.dynamic_tools_dir / f"{name}.py"
        file_content = f'"""Synthesized tool: {name}"""\n\n{function_code}\n'
        tool_file.write_text(file_content, encoding="utf-8")

        event_log.log_event(
            "tool_synthesized",
            source="tool_synthesizer",
            data={"name": name, "file": str(tool_file)},
        )

        logger.info("Successfully synthesized and registered tool '{}'", name)
        return {
            "status": "success",
            "tool_name": name,
            "file_path": str(tool_file),
            "description": description,
        }


tool_synthesizer = ToolSynthesizer()

__all__ = ["ToolSynthesizer", "tool_synthesizer"]
