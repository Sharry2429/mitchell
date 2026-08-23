"""Procedural Skill Synthesizer for "Teach Me" Mode.

Transforms recorded human demonstrations (clicks, keyboard input, navigation, commands)
into reusable, parameterized, and self-healing procedural skills.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.skills.library import skill_library
from mitchell.skills.schema import Skill, SkillStep
from mitchell.teaching.recorder import ActionRecorder, RecordedAction


class SkillSynthesisResult(BaseModel):
    """Result of compiling recorded actions into a reusable procedural skill."""

    skill_name: str
    description: str
    steps_count: int
    parameters: List[str]
    skill_object: Skill
    success: bool = True


class SkillSynthesizer:
    """Compiles human demonstrations into validated procedural skills."""

    def __init__(self, library=None) -> None:
        self.library = library or skill_library

    def synthesize_from_recorder(
        self,
        recorder: ActionRecorder,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> SkillSynthesisResult:
        """Synthesize and register a new Skill from an ActionRecorder's recorded buffer."""
        if not recorder.actions:
            raise ValueError("No actions recorded to synthesize a skill from.")

        parameterized_steps, param_schema = recorder.generalize_parameters()

        steps: List[SkillStep] = []
        for s in parameterized_steps:
            steps.append(
                SkillStep(
                    step_index=s["step_index"],
                    name=s["name"],
                    action_type=s["action_type"],
                    target=s["target"],
                    params=s["params"],
                    on_fail=s.get("on_fail", "abort"),
                )
            )

        clean_name = name.lower().replace(" ", "_").strip()
        skill = Skill(
            name=clean_name,
            description=description or f"Procedural workflow taught by user for '{name}'.",
            tags=tags or ["taught", "procedural", "custom"],
            source="teaching",
            required_tools=list(set([step.target for step in steps if step.action_type == "tool"])),
            parameters_schema=param_schema,
            steps=steps,
            confidence=0.92,
        )

        # Persist into Skill Library
        self.library.save_skill(skill)

        event_log.log_event(
            "skill_taught_and_synthesized",
            source="skill_synthesizer",
            data={"name": skill.name, "steps": len(steps), "parameters": list(param_schema.get("properties", {}).keys())},
        )

        logger.info("Synthesized new skill '{}' with {} steps and {} params", skill.name, len(steps), len(param_schema.get("properties", {})))

        return SkillSynthesisResult(
            skill_name=skill.name,
            description=skill.description,
            steps_count=len(steps),
            parameters=list(param_schema.get("properties", {}).keys()),
            skill_object=skill,
            success=True,
        )


skill_synthesizer = SkillSynthesizer()

__all__ = ["SkillSynthesisResult", "SkillSynthesizer", "skill_synthesizer"]
