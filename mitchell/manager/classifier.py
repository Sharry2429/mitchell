"""Goal Classifier determining intent domain, complexity, and worker routing."""

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class GoalClassification(BaseModel):
    """Structured assessment of user goal complexity and required pillars."""

    domain: Literal["browser", "windows", "android", "multi_pillar", "skill", "general"]
    complexity: Literal["simple_direct", "multi_step", "research_needed", "high_stakes", "ambiguous"]
    target_agents: List[str] = Field(default_factory=list)
    requires_council: bool = False
    confidence: float = 0.9
    reasoning: str = ""


class GoalClassifier:
    """Classifies incoming user prompts and goals for the Manager decision loop."""

    def classify(self, user_goal: str) -> GoalClassification:
        """Analyze text and determine domain, complexity, and routing requirements."""
        text = user_goal.lower().strip()

        # Domain signals
        has_browser = any(w in text for w in ["browser", "http", "https", "url", "website", "web", "scrape", "search", "html"])
        has_windows = any(w in text for w in ["window", "desktop", "notepad", "calc", "app", "exe", "explorer", "powershell"])
        has_android = any(w in text for w in ["android", "phone", "mobile", "adb", "scrcpy", "tap", "swipe", "wireless", "usb"])
        has_skill = any(w in text for w in ["skill", "procedure", "workflow", "recipe"])

        # High stakes / Ambiguous signals
        is_high_stakes = any(w in text for w in ["delete all", "wipe", "format", "critical", "danger", "irreversible", "deploy prod"])
        is_research = any(w in text for w in ["how to", "research", "investigate", "explore", "find out", "analyze", "compare"])

        # Domain resolution
        pillars_matched = sum([has_browser, has_windows, has_android])
        if pillars_matched > 1:
            domain = "multi_pillar"
            target_agents = ["browser_worker", "windows_worker", "android_worker"]
        elif has_browser:
            domain = "browser"
            target_agents = ["browser_worker"]
        elif has_windows:
            domain = "windows"
            target_agents = ["windows_worker"]
        elif has_android:
            domain = "android"
            target_agents = ["android_worker"]
        elif has_skill:
            domain = "skill"
            target_agents = ["skill_executor"]
        else:
            domain = "general"
            target_agents = []

        # Complexity resolution
        if is_high_stakes:
            complexity = "high_stakes"
            requires_council = True
            reasoning = "High-stakes intervention detected requiring multi-model critic/council review"
        elif is_research:
            complexity = "research_needed"
            requires_council = False
            reasoning = "Research workflow requiring information synthesis"
        elif pillars_matched > 1 or " then " in text or " and " in text:
            complexity = "multi_step"
            requires_council = False
            reasoning = "Multi-step workflow spanning multiple actions"
        else:
            complexity = "simple_direct"
            requires_council = False
            reasoning = "Direct single-intent task"

        return GoalClassification(
            domain=domain,
            complexity=complexity,
            target_agents=target_agents,
            requires_council=requires_council,
            confidence=0.92,
            reasoning=reasoning,
        )


goal_classifier = GoalClassifier()

__all__ = ["GoalClassification", "GoalClassifier", "goal_classifier"]
