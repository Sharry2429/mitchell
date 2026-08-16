"""
mitchell.core.fast_intent
=========================
Tier 0 / Tier 1 / Tier 2 fast path intent matching to skip LLM round-trips for routine commands.
"""

import json
from mitchell.core.tool_registry import get_registry
from mitchell.providers import active_provider

class FastIntentCache:
    def __init__(self):
        # A simple phrase-to-tool-call cache (Tier 0)
        self.exact_matches = {
            "mute my laptop": ("windows_hardware_set_volume", {"level": 0}),
            "unmute my laptop": ("windows_hardware_set_volume", {"level": 50}),
            "open chrome": ("windows_apps_open_app", {"name": "chrome"}),
            "lock my screen": ("windows_system_lock_screen", {}),
            "check battery": ("windows_hardware_get_battery", {})
        }

    def match_tier_0(self, text: str) -> tuple[str, dict] | None:
        """Tier 0: exact/fuzzy phrase match to a known tool."""
        text = text.lower().strip()
        return self.exact_matches.get(text)

    def match_tier_1(self, text: str) -> tuple[str, dict] | None:
        """
        Tier 1: cheap intent classifier.
        For now, a simple keyword matcher against tool descriptions.
        """
        registry = get_registry()
        text_lower = text.lower()
        
        # Extremely basic heuristic: if tool name matches exactly or closely and takes no args
        for name, func in registry.items():
            # Only auto-fire zero-arg tools to be safe on Tier 1
            if name.replace("_", " ") in text_lower:
                import inspect
                sig = inspect.signature(func)
                # Count required arguments
                req_args = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty]
                if len(req_args) == 0:
                    return (name, {})
        return None

    async def match_tier_2(self, text: str) -> tuple[str, dict] | None:
        """
        Tier 2: Single LLM call disambiguation.
        Uses the active provider's fastest model.
        """
        provider = active_provider()
        registry = get_registry()
        
        # Build tools schema for the LLM
        tools_schema = []
        for name, func in registry.items():
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": func.__doc__ or "Execute action",
                    "parameters": {"type": "object", "properties": {}}
                }
            })

        messages = [
            {"role": "system", "content": "You are a fast intent matcher. Output exactly ONE tool call that matches the user intent."},
            {"role": "user", "content": text}
        ]
        
        try:
            result = await provider.call(messages=messages, tools=tools_schema)
            if result.tool_calls:
                tcall = result.tool_calls[0]
                args = json.loads(tcall.function.arguments or "{}")
                return (tcall.function.name, args)
        except Exception:
            pass
        return None

_cache = FastIntentCache()

async def resolve_intent(text: str) -> tuple[str, dict] | None:
    """Resolve an intent through Tiers 0, 1, and 2."""
    match = _cache.match_tier_0(text)
    if match: return match
    
    match = _cache.match_tier_1(text)
    if match: return match
    
    return await _cache.match_tier_2(text)
