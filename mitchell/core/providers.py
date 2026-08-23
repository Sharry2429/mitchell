"""Multi-provider registry with health tracking, free-tier prioritization, and dynamic management.

Manages the full provider cascade: Groq → NVIDIA NIM → OpenRouter → DeepSeek → OpenAI → Anthropic → Gemini.
Tracks free-tier quotas, latency, error rates, and enables live switching at runtime.
"""

import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.logging import logger


class ProviderEndpoint(BaseModel):
    """Configuration for a single LLM API provider."""

    name: str = Field(..., description="Provider identifier")
    display_name: str = Field(..., description="Human-readable provider name")
    base_url: str = Field(..., description="API base URL")
    api_key_env: str = Field("", description="Environment variable name for API key")
    models: List[str] = Field(default_factory=list, description="Available model IDs")
    is_free_tier: bool = Field(default=False, description="Whether this provider offers free-tier access")
    free_tier_rpm: int = Field(default=0, description="Free-tier requests per minute limit")
    free_tier_rpd: int = Field(default=0, description="Free-tier requests per day limit")
    free_tier_tpd: int = Field(default=0, description="Free-tier tokens per day limit")
    supports_streaming: bool = Field(default=True, description="Supports streaming responses")
    supports_json_mode: bool = Field(default=True, description="Supports JSON output mode")
    headers_template: Dict[str, str] = Field(default_factory=dict, description="Extra headers")
    enabled: bool = Field(default=True, description="Whether this provider is currently enabled")


class ProviderHealth(BaseModel):
    """Health metrics for a provider."""

    name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    is_healthy: bool = True
    consecutive_failures: int = 0
    free_tier_requests_today: int = 0
    free_tier_tokens_today: int = 0
    free_tier_reset_date: Optional[str] = None


# ── Built-in provider definitions ─────────────────────────────────────────

BUILTIN_PROVIDERS: Dict[str, ProviderEndpoint] = {
    "groq": ProviderEndpoint(
        name="groq",
        display_name="Groq (Free Tier)",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        models=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "mixtral-8x7b-32768",
            "whisper-large-v3-turbo",
        ],
        is_free_tier=True,
        free_tier_rpm=30,
        free_tier_rpd=14400,
        free_tier_tpd=500_000,
        supports_streaming=True,
    ),
    "nvidia_nim": ProviderEndpoint(
        name="nvidia_nim",
        display_name="NVIDIA NIM",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_NIM_API_KEY",
        models=[
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.1-70b-instruct",
            "mistralai/mixtral-8x22b-instruct-v0.1",
            "google/gemma-2-27b-it",
        ],
        is_free_tier=True,
        free_tier_rpm=10,
        free_tier_rpd=1000,
        supports_streaming=True,
    ),
    "openrouter": ProviderEndpoint(
        name="openrouter",
        display_name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        models=[
            "meta-llama/llama-3.1-8b-instruct:free",
            "google/gemma-2-9b-it:free",
            "qwen/qwen-2.5-72b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
        ],
        is_free_tier=True,
        free_tier_rpm=20,
        free_tier_rpd=200,
        supports_streaming=True,
        headers_template={"HTTP-Referer": "https://mitchell.ai", "X-Title": "MitchellAI"},
    ),
    "deepseek": ProviderEndpoint(
        name="deepseek",
        display_name="DeepSeek",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        models=["deepseek-chat", "deepseek-reasoner"],
        is_free_tier=False,
        supports_streaming=True,
    ),
    "xai": ProviderEndpoint(
        name="xai",
        display_name="xAI (Grok)",
        base_url="https://api.x.ai/v1",
        api_key_env="XAI_API_KEY",
        models=["grok-2", "grok-beta"],
        is_free_tier=False,
        supports_streaming=True,
    ),
    "openai": ProviderEndpoint(
        name="openai",
        display_name="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        models=["gpt-4o", "gpt-4o-mini", "o3-mini", "o1", "gpt-4-turbo"],
        is_free_tier=False,
        supports_streaming=True,
    ),
    "anthropic": ProviderEndpoint(
        name="anthropic",
        display_name="Anthropic",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        models=["claude-3-7-sonnet-20250219", "claude-3-7-sonnet", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        is_free_tier=False,
        supports_streaming=True,
        supports_json_mode=False,
    ),
    "gemini": ProviderEndpoint(
        name="gemini",
        display_name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key_env="GEMINI_API_KEY",
        models=["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        is_free_tier=True,
        free_tier_rpm=15,
        free_tier_rpd=1500,
        supports_streaming=True,
    ),
}


class ProviderRegistry:
    """Dynamic provider management with health tracking, free-tier prioritization, and live switching.

    The registry maintains all provider configurations, monitors their health,
    tracks free-tier usage, and selects the optimal provider for each request
    based on the cascade configuration and current availability.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderEndpoint] = {}
        self._health: Dict[str, ProviderHealth] = {}
        self._active_provider: Optional[str] = None
        from mitchell.core.omniroute import omniroute
        omniroute.load_env_keys()
        self._load_builtin_providers()

    def _load_builtin_providers(self) -> None:
        """Load built-in provider definitions and resolve API keys."""
        for name, provider in BUILTIN_PROVIDERS.items():
            self._providers[name] = provider.model_copy()
            self._health[name] = ProviderHealth(name=name)

    # ── Provider Management ────────────────────────────────────────────────

    def add_provider(self, provider: ProviderEndpoint) -> None:
        """Register a new provider at runtime."""
        self._providers[provider.name] = provider
        self._health[provider.name] = ProviderHealth(name=provider.name)
        logger.info("Provider '{}' registered with {} models", provider.name, len(provider.models))

    def remove_provider(self, name: str) -> bool:
        """Remove a provider from the registry."""
        if name in self._providers:
            del self._providers[name]
            self._health.pop(name, None)
            logger.info("Provider '{}' removed", name)
            return True
        return False

    def enable_provider(self, name: str) -> bool:
        """Enable a provider."""
        if name in self._providers:
            self._providers[name].enabled = True
            return True
        return False

    def disable_provider(self, name: str) -> bool:
        """Disable a provider."""
        if name in self._providers:
            self._providers[name].enabled = False
            return True
        return False

    def get_provider(self, name: str) -> Optional[ProviderEndpoint]:
        """Get a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers with status."""
        result = []
        for name, prov in self._providers.items():
            health = self._health.get(name, ProviderHealth(name=name))
            api_key = self._resolve_api_key(name)
            result.append({
                "name": name,
                "display_name": prov.display_name,
                "enabled": prov.enabled,
                "has_api_key": bool(api_key),
                "is_free_tier": prov.is_free_tier,
                "models": prov.models,
                "is_healthy": health.is_healthy,
                "avg_latency_ms": round(health.avg_latency_ms, 1),
                "total_requests": health.total_requests,
                "success_rate": (
                    round(health.successful_requests / health.total_requests * 100, 1)
                    if health.total_requests > 0
                    else 100.0
                ),
            })
        return result

    # ── API Key Resolution ─────────────────────────────────────────────────

    def _resolve_api_key(self, provider_name: str) -> str:
        """Resolve API key from settings then environment variables."""
        prov = self._providers.get(provider_name)
        if not prov:
            return ""

        # Check settings first (MITCHELL_GROQ_API_KEY etc.)
        key_attr = f"{provider_name}_api_key"
        key = getattr(settings, key_attr, "")
        if key:
            return key

        # Check direct env vars
        if prov.api_key_env:
            key = os.getenv(prov.api_key_env, "")
            if key:
                return key

        # Check common aliases
        aliases = {
            "groq": ["GROQ_API_KEY"],
            "xai": ["XAI_API_KEY", "GROK_API_KEY"],
            "openai": ["OPENAI_API_KEY"],
            "deepseek": ["DEEPSEEK_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY"],
            "nvidia_nim": ["NVIDIA_NIM_API_KEY", "NVIDIA_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        }
        for alias in aliases.get(provider_name, []):
            val = os.getenv(alias, "")
            if val:
                return val

        return ""

    def get_api_key(self, provider_name: str) -> str:
        """Public API key resolver."""
        return self._resolve_api_key(provider_name)

    # ── Provider Selection ─────────────────────────────────────────────────

    def select_provider(
        self,
        task_type: str = "general",
        complexity: str = "medium",
        prefer_free: Optional[bool] = None,
        required_model: Optional[str] = None,
    ) -> Tuple[Optional[ProviderEndpoint], str, str]:
        """Select the best provider and model for a given task.

        Returns (provider, model_id, api_key) or (None, "", "") if no provider available.
        """
        if prefer_free is None:
            prefer_free = settings.free_tier_first

        # If a specific model is requested, find the provider that has it
        if required_model:
            for name, prov in self._providers.items():
                if not prov.enabled:
                    continue
                if required_model in prov.models or any(required_model in m for m in prov.models):
                    api_key = self._resolve_api_key(name)
                    if api_key:
                        return prov, required_model, api_key
            return None, "", ""

        # Build candidate list ordered by cascade priority
        cascade = settings.provider_cascade_list
        candidates: List[Tuple[ProviderEndpoint, str]] = []

        for prov_name in cascade:
            prov = self._providers.get(prov_name)
            if not prov or not prov.enabled:
                continue
            api_key = self._resolve_api_key(prov_name)
            if not api_key:
                continue
            health = self._health.get(prov_name)
            if health and not health.is_healthy:
                continue
            # Check free-tier quotas
            if prov.is_free_tier and health:
                if prov.free_tier_rpd > 0 and health.free_tier_requests_today >= prov.free_tier_rpd:
                    continue
            candidates.append((prov, api_key))

        if not candidates:
            return None, "", ""

        # Sort: free-tier first if preferred
        if prefer_free:
            candidates.sort(key=lambda c: (0 if c[0].is_free_tier else 1))

        # Select best model from the top provider
        prov, api_key = candidates[0]
        model = self._select_model_for_task(prov, task_type, complexity)
        return prov, model, api_key

    def _select_model_for_task(
        self, provider: ProviderEndpoint, task_type: str, complexity: str
    ) -> str:
        """Select the best model from a provider for a given task type."""
        models = provider.models
        if not models:
            return ""

        # For complex tasks, prefer larger models (first in list = usually largest)
        if complexity in ("high", "high_stakes"):
            return models[0]
        # For simple tasks, prefer smaller/faster models (last in list)
        if complexity == "low":
            return models[-1]
        # Medium — use second model if available, else first
        return models[1] if len(models) > 1 else models[0]

    # ── Health Tracking ────────────────────────────────────────────────────

    def record_success(self, provider_name: str, latency_ms: float, tokens_used: int = 0) -> None:
        """Record a successful request."""
        health = self._health.get(provider_name)
        if not health:
            return
        health.total_requests += 1
        health.successful_requests += 1
        health.total_latency_ms += latency_ms
        health.avg_latency_ms = health.total_latency_ms / health.total_requests
        health.last_success_time = datetime.now(timezone.utc)
        health.consecutive_failures = 0
        health.is_healthy = True
        health.free_tier_requests_today += 1
        health.free_tier_tokens_today += tokens_used
        self._check_daily_reset(health)

    def record_failure(self, provider_name: str, error: str) -> None:
        """Record a failed request."""
        health = self._health.get(provider_name)
        if not health:
            return
        health.total_requests += 1
        health.failed_requests += 1
        health.last_error = error
        health.last_error_time = datetime.now(timezone.utc)
        health.consecutive_failures += 1
        # Mark unhealthy after 3 consecutive failures
        if health.consecutive_failures >= 3:
            health.is_healthy = False
            logger.warning("Provider '{}' marked unhealthy after {} consecutive failures", provider_name, health.consecutive_failures)

    def reset_health(self, provider_name: str) -> None:
        """Reset health metrics for a provider."""
        if provider_name in self._health:
            self._health[provider_name] = ProviderHealth(name=provider_name)

    def get_health(self, provider_name: str) -> Optional[ProviderHealth]:
        """Get health metrics for a provider."""
        return self._health.get(provider_name)

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health summary for all providers."""
        return {name: h.model_dump() for name, h in self._health.items()}

    def _check_daily_reset(self, health: ProviderHealth) -> None:
        """Reset daily counters at midnight UTC."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if health.free_tier_reset_date != today:
            health.free_tier_requests_today = 0
            health.free_tier_tokens_today = 0
            health.free_tier_reset_date = today

    # ── Cascade Execution ──────────────────────────────────────────────────

    def get_cascade_order(self, prefer_free: bool = True) -> List[Tuple[ProviderEndpoint, str]]:
        """Get ordered list of (provider, api_key) for cascade fallback execution."""
        cascade = settings.provider_cascade_list
        result: List[Tuple[ProviderEndpoint, str]] = []

        for prov_name in cascade:
            prov = self._providers.get(prov_name)
            if not prov or not prov.enabled:
                continue
            api_key = self._resolve_api_key(prov_name)
            if not api_key:
                continue
            result.append((prov, api_key))

        if prefer_free:
            result.sort(key=lambda c: (0 if c[0].is_free_tier else 1))

        return result

    # ── Serialization ──────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """Get full registry state for Studio UI."""
        return {
            "providers": self.list_providers(),
            "health": self.get_all_health(),
            "cascade_order": settings.provider_cascade_list,
            "free_tier_first": settings.free_tier_first,
        }


# Global singleton
provider_registry = ProviderRegistry()

__all__ = [
    "ProviderEndpoint",
    "ProviderHealth",
    "ProviderRegistry",
    "provider_registry",
    "BUILTIN_PROVIDERS",
]
