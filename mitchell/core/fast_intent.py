"""
mitchell.core.fast_intent
The fast path for single-pillar direct actions.
"""
import re
from typing import Optional, Tuple, Any

# Tier 0: exact/fuzzy cache (seed set)
_INTENT_CACHE = {
    "mute my laptop": ("windows_hardware_mute", {}),
    "unmute my laptop": ("windows_hardware_unmute", {}),
    "lock my screen": ("windows_system_lock_screen", {}),
    "lock screen": ("windows_system_lock_screen", {}),
    "sleep": ("windows_system_sleep", {}),
}

def check_tier0(text: str) -> Optional[Tuple[str, dict]]:
    """Exact/fuzzy phrase match (Tier 0)."""
    clean_text = text.strip().lower()
    return _INTENT_CACHE.get(clean_text)

def check_tier1(text: str) -> Optional[Tuple[str, dict]]:
    """Cheap intent classifier (Tier 1)."""
    # Simple regex fallback for v1
    clean_text = text.strip().lower()
    
    # E.g. "open chrome"
    open_app_match = re.match(r"^open\s+(.+)$", clean_text)
    if open_app_match:
        app_name = open_app_match.group(1).strip()
        return ("windows_apps_open_app", {"name": app_name})
        
    return None

def resolve_intent(text: str) -> Optional[Tuple[str, dict]]:
    """
    Attempts to resolve the intent without an LLM round-trip.
    Returns (tool_name, args) if a fast path matches, else None.
    """
    res = check_tier0(text)
    if res:
        return res
        
    res = check_tier1(text)
    if res:
        return res
        
    # Tier 2 (LLM) is handled by the orchestrator if this returns None
    return None
