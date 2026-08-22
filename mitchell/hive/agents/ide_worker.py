"""IDE Worker Agent executing code editing, terminal commands, test runner, and Git tasks in Hive."""

import json
from typing import Any, Dict, Union

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent
from mitchell.ide import (
    code_editor,
    code_runner,
    git_manager,
    platform_bridges,
    project_scaffolder,
    terminal_manager,
)


class IDEWorkerAgent(BaseAgent):
    """Hive Agent specializing in software engineering, editing, testing, and terminal execution."""

    def __init__(
        self,
        agent_id: str = "ide_worker",
        description: str = "Executes multi-file code modifications, terminal commands, test suites, and Git workflows",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process IDE action."""
        logger.info("IDEWorker received task from {}: {}", sender, message)

        if isinstance(message, dict):
            action = message.get("action", "")
            data = message
        else:
            text = str(message).strip()
            parts = text.split(maxsplit=1)
            action = parts[0].lower() if parts else ""
            data = {"raw": parts[1]} if len(parts) > 1 else {}

        event_log.log_event(
            "ide_worker_task_started",
            source=self.agent_id,
            data={"action": action, "sender": sender},
        )

        try:
            if action in ("command", "run_cmd", "sh", "exec"):
                cmd = data.get("command") or data.get("raw") or ""
                cwd = data.get("cwd")
                res = terminal_manager.run_command(command=cmd, cwd=cwd)
                return {"status": "success", "result": res.model_dump(mode="json")}

            elif action in ("write_file", "edit"):
                path = data.get("path") or data.get("file_path") or ""
                content = data.get("content", "")
                res = code_editor.write_file(file_path=path, content=content)
                return {"status": "success", "result": res.model_dump(mode="json")}

            elif action in ("test", "pytest", "run_tests"):
                cwd = data.get("cwd")
                test_path = data.get("test_path")
                res = code_runner.run_tests(cwd=cwd, test_path=test_path)
                return {"status": "success", "result": res.model_dump(mode="json")}

            elif action in ("git", "git_status"):
                cwd = data.get("cwd")
                st = git_manager.status(repo_dir=cwd)
                return {"status": "success", "result": st.model_dump(mode="json")}

            elif action in ("scaffold", "create_project"):
                name = data.get("name") or "app"
                template = data.get("template", "python")
                manifest = project_scaffolder.create_project(name=name, template=template)
                return {"status": "success", "result": manifest.model_dump(mode="json")}

            return {"status": "success", "message": f"IDE task executed: {message}"}

        except Exception as e:
            logger.error("IDEWorker error: {}", e)
            return {"status": "error", "error": str(e)}


__all__ = ["IDEWorkerAgent"]
