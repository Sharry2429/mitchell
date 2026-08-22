"""Goal Classifier determining intent domain, complexity, and worker routing."""

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class GoalClassification(BaseModel):
    """Structured assessment of user goal complexity and required pillars."""

    domain: Literal[
        "browser",
        "windows",
        "android",
        "workspace",
        "ide",
        "comms",
        "media",
        "commerce",
        "iot",
        "multi_pillar",
        "skill",
        "general",
    ]
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
        has_workspace = any(w in text for w in ["document", "doc", "spreadsheet", "sheet", "csv", "note", "kanban", "board", "calendar", "mail"])
        has_ide = any(w in text for w in ["code", "refactor", "pytest", "test", "git", "commit", "terminal", "run command", "scaffold project", "python file"])
        has_comms = any(w in text for w in ["whatsapp", "sms", "text message", "call", "inbox", "scheduled message", "chat"])
        has_media = any(w in text for w in ["spotify", "music", "play song", "download video", "youtube", "download", "movie recommendation"])
        has_commerce = any(w in text for w in ["price", "product", "deal", "coupon", "amazon", "flipkart", "cart", "buy"])
        has_iot = any(w in text for w in ["light", "scene", "cinema mode", "living room", "temperature", "ac", "thermostat", "smart home", "vacuum"])
        has_browser = any(w in text for w in ["browser", "http", "https", "url", "website", "web", "scrape", "search online", "html"])
        has_windows = any(w in text for w in ["window", "desktop", "notepad", "calc", "app", "exe", "explorer", "powershell"])
        has_android = any(w in text for w in ["android", "phone", "mobile", "adb", "scrcpy", "tap", "swipe", "wireless", "usb"])
        has_skill = any(w in text for w in ["skill", "procedure", "workflow", "recipe"])

        # High stakes / Ambiguous signals
        is_high_stakes = any(w in text for w in ["delete all", "wipe", "format", "critical", "danger", "irreversible", "deploy prod"])
        is_research = any(w in text for w in ["how to", "research", "investigate", "explore", "find out", "analyze", "compare"])

        # Domain resolution
        pillars_matched = sum([has_browser, has_windows, has_android, has_workspace, has_ide, has_comms, has_media, has_commerce, has_iot])

        if pillars_matched > 1:
            domain = "multi_pillar"
            target_agents = ["browser_worker", "windows_worker", "android_worker", "workspace_worker"]
        elif has_workspace:
            domain = "workspace"
            target_agents = ["workspace_worker"]
        elif has_ide:
            domain = "ide"
            target_agents = ["ide_worker"]
        elif has_comms:
            domain = "comms"
            target_agents = ["comms_worker"]
        elif has_media:
            domain = "media"
            target_agents = ["media_worker"]
        elif has_commerce:
            domain = "commerce"
            target_agents = ["commerce_worker"]
        elif has_iot:
            domain = "iot"
            target_agents = ["iot_worker"]
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
            confidence=0.95,
            reasoning=reasoning,
        )


goal_classifier = GoalClassifier()

__all__ = ["GoalClassification", "GoalClassifier", "goal_classifier"]
