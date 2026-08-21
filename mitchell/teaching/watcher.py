"""Teaching Session Coordinator for Watch Me demonstrations."""

import time
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.self_model import self_model
from mitchell.skills.library import skill_library
from mitchell.skills.schema import Skill, SkillStep
from mitchell.teaching.recorder import ActionRecorder


class TeachingWatcher:
    """Coordinates 'Watch Me' interactive teaching sessions and synthesizes procedural skills."""

    def __init__(self) -> None:
        self.recorder = ActionRecorder()
        self.library = skill_library
        self.self_model = self_model
        self.current_skill_name: Optional[str] = None
        self.current_description: str = ""
        self.is_active: bool = False

    def start_session(self, skill_name: str, description: str = "") -> Dict[str, Any]:
        """Start a new 'Watch Me' observation session."""
        self.recorder.clear()
        self.current_skill_name = skill_name
        self.current_description = description or f"User demonstrated procedural skill '{skill_name}'"
        self.is_active = True

        logger.info("Teaching session started for skill '{}'", skill_name)
        event_log.log_event(
            "teaching_session_started",
            source="teaching_watcher",
            data={"skill_name": skill_name, "description": self.current_description},
        )

        return {
            "status": "active",
            "message": f"Watching mode active for skill '{skill_name}'. Demonstrate your actions now.",
        }

    def record_step(self, action_type: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Record an observed action step in the current session."""
        if not self.is_active:
            return {"status": "error", "message": "No active teaching session. Call start_session first."}

        act = self.recorder.add_action(action_type, target, params, timestamp=time.time())
        logger.info("Teaching: Recorded step {} -> {} ({})", act.index, act.target, act.params)

        return {
            "status": "step_recorded",
            "step_index": act.index,
            "target": act.target,
        }

    def finalize_skill(self, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Complete teaching session, synthesize generalized skill, and save to Skill Library."""
        if not self.is_active or not self.current_skill_name:
            return {"status": "error", "message": "No active teaching session to finalize"}

        if not self.recorder.actions:
            self.is_active = False
            return {"status": "error", "message": "Zero actions recorded during teaching session"}

        steps_data, param_schema = self.recorder.generalize_parameters()

        skill_steps = [
            SkillStep(
                step_index=s["step_index"],
                name=s["name"],
                action_type=s["action_type"],
                target=s["target"],
                params=s["params"],
                on_fail=s["on_fail"],
            )
            for s in steps_data
        ]

        skill = Skill(
            name=self.current_skill_name,
            description=self.current_description,
            tags=tags or ["taught", "custom", "demonstration"],
            source="teaching",
            source_refs=["human_demonstration"],
            parameters_schema=param_schema,
            steps=skill_steps,
            confidence=0.95,
        )

        self.library.save_skill(skill)
        self.self_model.record_run(
            capability_name=f"skill:{skill.name}",
            category="skill",
            success=True,
            duration_s=0.0,
        )

        event_log.log_event(
            "teaching_session_completed",
            source="teaching_watcher",
            data={"skill_name": skill.name, "steps_count": len(skill.steps)},
        )

        self.is_active = False
        logger.info("Teaching: Successfully created and registered skill '{}'", skill.name)

        return {
            "status": "success",
            "message": f"Successfully created and saved taught skill '{skill.name}' with {len(skill.steps)} steps!",
            "skill": skill.model_dump(),
        }


teaching_watcher = TeachingWatcher()

__all__ = ["TeachingWatcher", "teaching_watcher"]
