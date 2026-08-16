"""
Provider registry and active provider management.
"""
from typing import Optional, Any
from mitchell.providers.base import Provider
from mitchell.providers.groq import GroqProvider
from mitchell.providers.aicredits import AiCreditsProvider

_providers: dict[str, Provider] = {}
_active_provider_name: Optional[str] = None
_cascade: list[str] = ["groq", "aicredits"]

def load_providers():
    """Initialize the configured providers."""
    global _providers
    _providers["groq"] = GroqProvider()
    _providers["aicredits"] = AiCreditsProvider()

def get_provider(name: str) -> Optional[Provider]:
    """Get a provider by name."""
    if not _providers:
        load_providers()
    return _providers.get(name)

def active_provider() -> Provider:
    """Get the currently active provider, or default to the first in cascade."""
    if not _providers:
        load_providers()
        
    if _active_provider_name and _active_provider_name in _providers:
        return _providers[_active_provider_name]
        
    # Default to first available in cascade
    for name in _cascade:
        if name in _providers:
            return _providers[name]
            
    raise RuntimeError("No providers configured or available.")

def set_active(name: str) -> bool:
    """Set the pinned active provider. Returns True if found."""
    if not _providers:
        load_providers()
        
    if name in _providers:
        global _active_provider_name
        _active_provider_name = name
        return True
    return False

def cascade_order() -> list[Provider]:
    """Get providers in fallback cascade order. Pinned provider goes first."""
    if not _providers:
        load_providers()
        
    order = []
    if _active_provider_name and _active_provider_name in _providers:
        order.append(_providers[_active_provider_name])
        
    for name in _cascade:
        if name != _active_provider_name and name in _providers:
            order.append(_providers[name])
            
    return order

async def cascading_call(tier: str, messages: list[dict], tools: list[dict] = None, task_id: str = None) -> Any:
    """Try providers in cascade order until one succeeds."""
    last_error = None
    for provider in cascade_order():
        try:
            return await provider.call(messages=messages, tools=tools)
        except Exception as e:
            last_error = e
            print(f"Provider {provider.__class__.__name__} failed: {e}. Falling back...")
            continue
            
    raise RuntimeError(f"All providers in cascade failed. Last error: {last_error}")

import asyncio

async def warm_ping():
    """Send a trivial keep-alive ping to the active provider to pre-warm the TLS connection."""
    try:
        provider = active_provider()
        # A tiny prompt that the model can answer in 1 token
        messages = [{"role": "user", "content": "Ping. Reply 'Pong'."}]
        await provider.call(messages=messages, max_tokens=2)
    except Exception:
        pass
