"""Search -> Learn -> Remember pipeline for autonomous skill acquisition."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.self_model import self_model
from mitchell.skills.executor import skill_executor
from mitchell.skills.library import skill_library
from mitchell.skills.schema import Skill, SkillStep
from mitchell.tools.registry import tool_registry


class SkillLearner:
    """Detects capability gaps, synthesizes new procedural skills, tests them, and stores them."""

    def __init__(self) -> None:
        self.library = skill_library
        self.executor = skill_executor
        self.tools = tool_registry
        self.self_model = self_model

    def detect_gap(self, goal: str) -> bool:
        """Check if an existing skill or direct tool can fulfill the goal."""
        matching_skills = self.library.search_skills(goal, top_k=1)
        if matching_skills and matching_skills[0].confidence > 0.75:
            return False  # Capable
        return True  # Gap detected

    def synthesize_skill(
        self,
        goal: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
        source_refs: Optional[List[str]] = None,
    ) -> Skill:
        """Synthesize a new draft skill from structured research or planner steps."""
        logger.info("SkillLearner: Synthesizing skill '{}' for goal: {}", name, goal)

        skill_steps = [
            SkillStep(
                step_index=i + 1,
                name=s.get("name", f"step_{i+1}"),
                action_type=s.get("action_type", "tool"),
                target=s.get("target", ""),
                params=s.get("params", {}),
                on_fail=s.get("on_fail", "abort"),
                fallback_target=s.get("fallback_target"),
            )
            for i, s in enumerate(steps)
        ]

        skill = Skill(
            name=name,
            description=description,
            tags=tags or ["learned", "organic"],
            source="organic",
            source_refs=source_refs or [goal],
            steps=skill_steps,
            confidence=0.7,
        )

        return skill

    def learn_and_remember(
        self,
        goal: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        test_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Complete Search -> Learn -> Remember flow:
        1. Synthesize candidate skill
        2. Test execution under observation
        3. On success: persist in SkillLibrary and register in SelfModel
        """
        logger.info("SkillLearner: Executing Search -> Learn -> Remember for '{}'", name)
        event_log.log_event(
            "skill_learning_started",
            source="skill_learner",
            data={"goal": goal, "name": name},
        )

        skill = self.synthesize_skill(goal=goal, name=name, description=description, steps=steps)

        # Test execution
        exec_res = self.executor.execute(skill, parameters=test_params or {})

        if exec_res.get("success"):
            skill.confidence = 0.85
            self.library.save_skill(skill)

            # Update SelfModel
            self.self_model.record_run(
                capability_name=f"skill:{skill.name}",
                category="skill",
                success=True,
                duration_s=exec_res.get("duration_s", 0.0),
            )

            event_log.log_event(
                "skill_learned_successfully",
                source="skill_learner",
                data={"skill_name": skill.name, "steps": len(skill.steps)},
            )
            logger.info("SkillLearner: Skill '{}' verified and permanently remembered!", skill.name)
            return {
                "success": True,
                "message": f"Successfully learned and saved skill '{skill.name}'",
                "skill": skill.model_dump(),
            }
        else:
            logger.warning("SkillLearner: Verification failed for '{}': {}", name, exec_res.get("error"))
            return {
                "success": False,
                "error": f"Skill verification failed: {exec_res.get('error')}",
            }


skill_learner = SkillLearner()

__all__ = ["SkillLearner", "skill_learner"]
