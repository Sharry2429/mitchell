"""Self-Evolution Engine coordinating codebase introspection, tool synthesis, and self-patching."""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.evolution.inspector import code_inspector
from mitchell.evolution.patcher import self_patcher
from mitchell.evolution.synthesizer import tool_synthesizer


class SelfEvolutionEngine:
    """Master engine enabling Mitchell to inspect, synthesize tools, and evolve itself."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path(__file__).resolve().parent.parent.parent
        self.inspector = code_inspector
        self.synthesizer = tool_synthesizer
        self.patcher = self_patcher

    def run_test_suite(self, test_path: str = "tests/test_full_system.py") -> Dict[str, Any]:
        """Execute the pytest verification suite and return pass/fail metrics."""
        try:
            cmd = [sys.executable, "-m", "pytest", test_path, "-q"]
            res = subprocess.run(cmd, cwd=str(self.root_dir), capture_output=True, text=True, timeout=60)
            passed = (res.returncode == 0)
            return {
                "success": passed,
                "returncode": res.returncode,
                "stdout": res.stdout[-500:] if res.stdout else "",
                "stderr": res.stderr[-500:] if res.stderr else "",
            }
        except Exception as e:
            logger.error("Failed to run test suite: {}", e)
            return {"success": False, "error": str(e)}

    def evolve_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function_code: str,
        verify_tests: bool = True,
    ) -> Dict[str, Any]:
        """Synthesize a new tool, optionally verifying that the full system test suite still passes."""
        synth_res = self.synthesizer.synthesize_tool(
            name=name,
            description=description,
            parameters=parameters,
            function_code=function_code,
        )

        if synth_res.get("status") != "success":
            return synth_res

        if verify_tests:
            test_res = self.run_test_suite()
            if not test_res.get("success"):
                logger.warning("Test suite failed after synthesizing tool '{}'.", name)
                synth_res["test_status"] = "failed"
                synth_res["test_details"] = test_res
            else:
                synth_res["test_status"] = "passed"

        event_log.log_event(
            "self_evolution_cycle_completed",
            source="self_evolution_engine",
            data={"tool_name": name, "test_status": synth_res.get("test_status")},
        )
        return synth_res

    def diagnose_and_heal(self, error_trace: str) -> Dict[str, Any]:
        """Diagnose a runtime crash trace and propose candidate remediation."""
        diagnosis = self.patcher.diagnose_traceback(error_trace)
        return {
            "status": "diagnosed",
            "diagnosis": diagnosis,
            "can_auto_patch": bool(diagnosis.get("candidate_file")),
        }


evolution_engine = SelfEvolutionEngine()

__all__ = ["SelfEvolutionEngine", "evolution_engine"]
