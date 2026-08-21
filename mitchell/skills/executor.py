"""Step-by-step Skill Executor with parameter substitution and recovery policies."""

import re
import time
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.router import hive_router
from mitchell.memory.self_model import self_model
from mitchell.skills.library import skill_library
from mitchell.skills.schema import Skill, SkillStep
from mitchell.tools.registry import tool_registry


def _substitute_templates(obj: Any, params: Dict[str, Any]) -> Any:
    """Recursively replace {{param_name}} placeholders with actual values."""
    if isinstance(obj, str):
        result = obj
        for k, v in params.items():
            result = result.replace(f"{{{{{k}}}}}", str(v))
        return result
    elif isinstance(obj, dict):
        return {k: _substitute_templates(v, params) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_templates(item, params) for item in obj]
    return obj


class SkillExecutor:
    """Executes procedural skills with error handling and parameter resolution."""

    def __init__(self) -> None:
        self.library = skill_library
        self.tools = tool_registry
        self.hive = hive_router
        self.self_model = self_model

    def execute(
        self,
        skill_or_name: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a skill step-by-step."""
        params = parameters or {}

        if isinstance(skill_or_name, str):
            skill = self.library.get_skill(skill_or_name)
            if not skill:
                return {"success": False, "error": f"Skill '{skill_or_name}' not found in library"}
        else:
            skill = skill_or_name

        start_time = time.time()
        logger.info("SkillExecutor: Starting skill '{}' ({} steps)", skill.name, len(skill.steps))

        event_log.log_event(
            "skill_execution_started",
            source="skill_executor",
            data={"skill_name": skill.name, "parameters": params},
        )

        step_results: List[Dict[str, Any]] = []
        overall_success = True
        error_msg: Optional[str] = None

        for step in skill.steps:
            resolved_params = _substitute_templates(step.params, params)
            logger.info("Executing step [{}] '{}' ({})", step.step_index, step.name, step.target)

            step_res = self._execute_step(step, resolved_params)
            step_results.append({
                "step_index": step.step_index,
                "name": step.name,
                "target": step.target,
                "success": step_res.get("success", False),
                "output": step_res.get("output"),
            })

            if not step_res.get("success"):
                if step.on_fail == "retry":
                    logger.warning("Step '{}' failed, retrying once...", step.name)
                    time.sleep(0.5)
                    step_res = self._execute_step(step, resolved_params)
                    if step_res.get("success"):
                        continue

                if step.on_fail == "fallback" and step.fallback_target:
                    logger.warning("Step '{}' failed, attempting fallback target '{}'", step.name, step.fallback_target)
                    fallback_step = step.model_copy(update={"target": step.fallback_target})
                    step_res = self._execute_step(fallback_step, resolved_params)
                    if step_res.get("success"):
                        continue

                if step.on_fail == "abort":
                    overall_success = False
                    error_msg = f"Step {step.step_index} ('{step.name}') failed: {step_res.get('error')}"
                    logger.error("Skill '{}' aborted: {}", skill.name, error_msg)
                    break
                elif step.on_fail == "ignore":
                    logger.info("Step '{}' failed but on_fail='ignore'. Continuing...", step.name)

        duration = round(time.time() - start_time, 2)

        # Update stats
        self.library.update_stats(skill.name, success=overall_success, duration_s=duration)
        self.self_model.record_run(
            capability_name=f"skill:{skill.name}",
            category="skill",
            success=overall_success,
            duration_s=duration,
        )

        event_log.log_event(
            "skill_execution_finished",
            source="skill_executor",
            data={
                "skill_name": skill.name,
                "success": overall_success,
                "duration_s": duration,
                "steps_completed": len(step_results),
            },
        )

        return {
            "success": overall_success,
            "skill_name": skill.name,
            "duration_s": duration,
            "error": error_msg,
            "steps": step_results,
        }

    def _execute_step(self, step: SkillStep, resolved_params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a single step to tool, agent, or fast intent."""
        try:
            if step.action_type == "tool":
                tool = self.tools.get(step.target)
                if not tool:
                    return {"success": False, "error": f"Tool '{step.target}' not found"}
                res = tool(**resolved_params)
                return {"success": True, "output": str(res)}

            elif step.action_type == "agent":
                res = self.hive.send_message(agent_id=step.target, message=resolved_params, sender="skill_executor")
                return {"success": True, "output": str(res)}

            return {"success": False, "error": f"Unsupported action type '{step.action_type}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}


skill_executor = SkillExecutor()

__all__ = ["SkillExecutor", "skill_executor"]
