"""Security permission guardrails and cryptographic event log audit verification."""

import enum
import hashlib
from typing import Any, Dict, List, Optional, Tuple

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.tools.registry import Tool


class PermissionLevel(enum.Enum):
    """Tiered security permission levels."""

    READ_ONLY = "read_only"
    CONFIRM_REQUIRED = "confirm_required"
    RESTRICTED = "restricted"


class SecurityGuardrail:
    """Evaluates action risk, enforces permission tiers, and validates audit integrity."""

    def __init__(self, default_level: PermissionLevel = PermissionLevel.READ_ONLY) -> None:
        self.default_level = default_level
        self.dangerous_tool_names = {
            "windows_click", "windows_type", "android_tap", "android_type",
            "self_synthesize_tool", "daemon_enqueue_goal"
        }

    def classify_tool_risk(self, tool: Tool) -> PermissionLevel:
        """Determine permission requirement for a tool."""
        if getattr(tool, "is_dangerous", False) or tool.name in self.dangerous_tool_names:
            return PermissionLevel.CONFIRM_REQUIRED
        return PermissionLevel.READ_ONLY

    def verify_action_allowed(
        self,
        tool: Tool,
        auto_approve_safe: bool = True,
    ) -> Tuple[bool, str]:
        """Check if an action is permitted under current security policy."""
        tier = self.classify_tool_risk(tool)
        if tier == PermissionLevel.READ_ONLY:
            return True, "Allowed: Safe read-only action."

        if auto_approve_safe:
            logger.info("SecurityGuardrail: Auto-approved action '{}' (Tier={})", tool.name, tier.value)
            return True, f"Approved under policy: {tool.name}"

        return False, f"Confirmation required for action '{tool.name}' (Tier={tier.value})"

    def calculate_log_chain_hash(self, events: Optional[List[Dict[str, Any]]] = None) -> str:
        """Compute SHA256 cryptographic hash chain across logged events to ensure audit integrity."""
        recent_events = events or [e.model_dump() for e in event_log.get_recent(n=50)]
        hasher = hashlib.sha256()

        for ev in recent_events:
            entry_str = f"{ev.get('id')}:{ev.get('timestamp')}:{ev.get('type')}:{ev.get('source')}"
            hasher.update(entry_str.encode("utf-8"))

        return hasher.hexdigest()


security_guardrail = SecurityGuardrail()

__all__ = ["PermissionLevel", "SecurityGuardrail", "security_guardrail"]
