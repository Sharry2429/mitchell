import logging
from typing import List, Optional
from mitchell.providers.base import Provider
from mitchell.providers.groq import GroqProvider
from mitchell.providers.aicredits import AiCreditsProvider

logger = logging.getLogger("mitchell.providers.registry")

_PROVIDERS: dict[str, Provider] = {}
_CASCADE: List[str] = ["groq", "aicredits"]
_ACTIVE_PROVIDER: Optional[str] = None
_PINNED_MODEL: Optional[str] = None

def register_provider(provider: Provider):
    _PROVIDERS[provider.name.lower()] = provider

def load_providers():
    register_provider(GroqProvider())
    register_provider(AiCreditsProvider())

def active_provider() -> Provider:
    if _ACTIVE_PROVIDER and _ACTIVE_PROVIDER in _PROVIDERS:
        return _PROVIDERS[_ACTIVE_PROVIDER]
    
    if _CASCADE and _CASCADE[0] in _PROVIDERS:
        return _PROVIDERS[_CASCADE[0]]
        
    raise RuntimeError("No active provider found")

def set_active(name: str):
    global _ACTIVE_PROVIDER
    if name.lower() in _PROVIDERS:
        _ACTIVE_PROVIDER = name.lower()
    else:
        raise ValueError(f"Unknown provider: {name}")

def set_active_model(model: str):
    global _PINNED_MODEL
    _PINNED_MODEL = model

def get_active_model() -> Optional[str]:
    return _PINNED_MODEL

def cascade_order() -> List[Provider]:
    return [_PROVIDERS[name] for name in _CASCADE if name in _PROVIDERS]

def warm_ping():
    try:
        provider = active_provider()
        provider.warm_ping()
    except Exception as e:
        logger.warning(f"Warm ping failed: {e}")

# Load providers on module import
load_providers()
