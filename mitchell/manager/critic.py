"""Plan Critic pass validating safety, preconditions, and simplicity before execution."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.manager.planner import TaskGraph


class CriticEvaluation(BaseModel):
    """Structured review of a candidate task plan."""

    approved: bool = True
    score: float = 0.95
    critiques: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    safety_check_passed: bool = True


class PlanCritic:
    """Evaluates task graphs against safety checks, simplicity principles, and tool requirements."""

    def evaluate(self, plan: TaskGraph) -> CriticEvaluation:
        """Evaluate synthesized plan before execution."""
        logger.info("PlanCritic: Evaluating plan '{}' ({} nodes)", plan.id, len(plan.nodes))

        critiques: List[str] = []
        suggestions: List[str] = []
        safety_passed = True

        # 1. Safety check
        dangerous_keywords = ["rm -rf", "drop database", "format c:", "delete all"]
        for node in plan.nodes:
            payload_str = str(node.payload).lower()
            if any(kw in payload_str for kw in dangerous_keywords):
                safety_passed = False
                critiques.append(f"Potentially destructive action detected in step '{node.title}'")

        # 2. Complexity check (Simplicity First)
        if len(plan.nodes) > 8:
            suggestions.append("Consider breaking down large plan into smaller milestone chunks")

        # 3. Empty plan check
        if not plan.nodes:
            critiques.append("Plan contains zero executable nodes")

        approved = safety_passed and len(critiques) == 0
        score = 0.95 if approved else 0.4

        eval_result = CriticEvaluation(
            approved=approved,
            score=score,
            critiques=critiques,
            suggestions=suggestions,
            safety_check_passed=safety_passed,
        )

        event_log.log_event(
            "plan_critic_evaluated",
            source="plan_critic",
            data={
                "plan_id": plan.id,
                "approved": approved,
                "score": score,
                "critiques_count": len(critiques),
            },
        )

        return eval_result


plan_critic = PlanCritic()

__all__ = ["CriticEvaluation", "PlanCritic", "plan_critic"]
