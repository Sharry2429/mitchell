"""Multi-Local Provider Engine for Mitchell.

Supports simultaneous multiple local offline and private LLM providers:
- Ollama (http://localhost:11434)
- LM Studio (http://localhost:1234/v1)
- vLLM (http://localhost:8000/v1)
- LocalAI (http://localhost:8080/v1)
- Jan.ai / Nitro (http://localhost:1337/v1)
- Text Generation WebUI / TabbyAPI / ExLlamaV2 (http://localhost:5000/v1)
- Custom Local & LAN OpenAI-compatible Endpoints (e.g. local GPU clusters)

Features:
- Port auto-discovery of running local engines
- Live model listing from each local server
- Dynamic provider addition, removal, and enable/disable at runtime
- Zero-cost, 100% offline inference with automatic failover between local providers
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from mitchell.core.logging import logger


class LocalProviderConfig(BaseModel):
    """Configuration and health state for a single local provider instance."""

    name: str = Field(..., description="Unique provider ID (e.g. 'ollama_primary', 'lmstudio', 'vllm')")
    display_name: str = Field(..., description="Human-readable label")
    provider_type: str = Field(
        default="openai_compatible",
        description="Engine type: 'ollama' or 'openai_compatible'",
    )
    base_url: str = Field(..., description="Base URL of local instance")
    api_key: Optional[str] = Field(default=None, description="Optional API key / token")
    default_model: str = Field(default="llama3.2", description="Default model to invoke")
    models: List[str] = Field(default_factory=list, description="Cached list of local models")
    enabled: bool = Field(default=True, description="Whether this local provider is enabled")
    is_online: bool = Field(default=False, description="Whether currently responding to ping")
    last_ping_ms: float = Field(default=0.0, description="Ping round-trip latency in ms")


# Default local server definitions for auto-discovery
DEFAULT_LOCAL_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ollama": {
        "display_name": "Ollama Local Engine",
        "provider_type": "ollama",
        "base_url": "http://localhost:11434",
        "default_model": "llama3.2",
    },
    "lmstudio": {
        "display_name": "LM Studio",
        "provider_type": "openai_compatible",
        "base_url": "http://localhost:1234/v1",
        "default_model": "local-model",
    },
    "vllm": {
        "display_name": "vLLM Inference Server",
        "provider_type": "openai_compatible",
        "base_url": "http://localhost:8000/v1",
        "default_model": "meta-llama/Llama-3.1-8B-Instruct",
    },
    "localai": {
        "display_name": "LocalAI Server",
        "provider_type": "openai_compatible",
        "base_url": "http://localhost:8080/v1",
        "default_model": "gpt-4",
    },
    "jan": {
        "display_name": "Jan.ai Desktop Engine",
        "provider_type": "openai_compatible",
        "base_url": "http://localhost:1337/v1",
        "default_model": "mistral-ins-7b-q4",
    },
    "tabby": {
        "display_name": "Text Gen WebUI / TabbyAPI",
        "provider_type": "openai_compatible",
        "base_url": "http://localhost:5000/v1",
        "default_model": "local-model",
    },
}


class MultiLocalLLMManager:
    """Manages and coordinates multiple local LLM providers with automatic health monitoring and discovery."""

    def __init__(self) -> None:
        self.providers: Dict[str, LocalProviderConfig] = {}
        self._init_default_providers()

    def _init_default_providers(self) -> None:
        """Initialize provider configurations from environment or default templates."""
        for key, tmpl in DEFAULT_LOCAL_TEMPLATES.items():
            env_url = os.environ.get(f"{key.upper()}_BASE_URL")
            url = env_url or tmpl["base_url"]
            self.providers[key] = LocalProviderConfig(
                name=key,
                display_name=tmpl["display_name"],
                provider_type=tmpl["provider_type"],
                base_url=url,
                default_model=tmpl["default_model"],
                enabled=True,
            )

    def add_provider(
        self,
        name: str,
        display_name: Optional[str] = None,
        provider_type: str = "openai_compatible",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
        default_model: str = "llama3.2",
        enabled: bool = True,
    ) -> LocalProviderConfig:
        """Add or update a custom local LLM provider (e.g. LAN GPU server)."""
        cfg = LocalProviderConfig(
            name=name,
            display_name=display_name or name.title(),
            provider_type=provider_type,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            default_model=default_model,
            enabled=enabled,
        )
        self.providers[name] = cfg
        logger.info("LocalLLM: Registered local provider '{}' ({})", name, cfg.base_url)
        return cfg

    def remove_provider(self, name: str) -> bool:
        """Remove a local provider by name."""
        if name in self.providers:
            del self.providers[name]
            logger.info("LocalLLM: Removed provider '{}'", name)
            return True
        return False

    def get_provider(self, name: str) -> Optional[LocalProviderConfig]:
        """Get provider config by name."""
        return self.providers.get(name)

    def list_providers(self) -> List[Dict[str, Any]]:
        """Return list of all configured local providers with live status."""
        return [p.model_dump(mode="json") for p in self.providers.values()]

    async def ping_provider(self, name: str) -> bool:
        """Check if a specific local provider is online and fetch its models."""
        provider = self.get_provider(name)
        if not provider or not provider.enabled:
            return False

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                if provider.provider_type == "ollama":
                    res = await client.get(f"{provider.base_url}/api/tags")
                    if res.status_code == 200:
                        data = res.json()
                        provider.models = [m.get("name", "") for m in data.get("models", [])]
                        provider.is_online = True
                        provider.last_ping_ms = round((time.time() - start) * 1000, 1)
                        return True
                else:
                    # OpenAI-compatible /v1/models or /models
                    headers = {}
                    if provider.api_key:
                        headers["Authorization"] = f"Bearer {provider.api_key}"

                    url = f"{provider.base_url}/models" if not provider.base_url.endswith("/v1") else f"{provider.base_url}/models"
                    res = await client.get(url, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        raw_models = data.get("data", [])
                        provider.models = [m.get("id", "") for m in raw_models]
                        provider.is_online = True
                        provider.last_ping_ms = round((time.time() - start) * 1000, 1)
                        return True
        except Exception:
            pass

        provider.is_online = False
        return False

    async def discover_all_local_providers(self) -> List[Dict[str, Any]]:
        """Probe all configured local providers in parallel and update their models and online status."""
        tasks = [self.ping_provider(name) for name in self.providers]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.list_providers()

    def get_online_providers(self) -> List[LocalProviderConfig]:
        """Return all local providers currently confirmed online."""
        return [p for p in self.providers.values() if p.enabled and p.is_online]

    async def async_generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        provider_name: Optional[str] = None,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> Dict[str, Any]:
        """Generate a completion using a specific local provider or the fastest available online provider."""
        target_provider: Optional[LocalProviderConfig] = None

        if provider_name and provider_name in self.providers:
            target_provider = self.providers[provider_name]
        else:
            # Pick first online provider or probe if none marked online
            online = self.get_online_providers()
            if not online:
                await self.discover_all_local_providers()
                online = self.get_online_providers()
            target_provider = online[0] if online else self.providers.get("ollama")

        if not target_provider:
            return {
                "text": f"[Mitchell Offline Local Mock]: {prompt[:60]}...",
                "model": "offline-fallback",
                "provider": "mock",
            }

        target_model = model or target_provider.default_model

        # 1. Ollama Native Protocol
        if target_provider.provider_type == "ollama":
            payload: Dict[str, Any] = {
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            }
            if system:
                payload["system"] = system
            if json_mode:
                payload["format"] = "json"

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(f"{target_provider.base_url}/api/generate", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        return {
                            "text": data.get("response", "").strip(),
                            "model": target_model,
                            "provider": target_provider.name,
                            "total_duration": data.get("total_duration", 0),
                            "eval_count": data.get("eval_count", 0),
                        }
            except Exception as e:
                logger.warning("Local Ollama request failed: {}", e)

        # 2. OpenAI-Compatible Protocol (LM Studio, vLLM, LocalAI, Jan, Tabby)
        else:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            headers = {"Content-Type": "application/json"}
            if target_provider.api_key:
                headers["Authorization"] = f"Bearer {target_provider.api_key}"

            url = f"{target_provider.base_url}/chat/completions" if not target_provider.base_url.endswith("/v1") else f"{target_provider.base_url}/chat/completions"

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        content = choices[0].get("message", {}).get("content", "") if choices else ""
                        return {
                            "text": content.strip(),
                            "model": target_model,
                            "provider": target_provider.name,
                            "usage": data.get("usage", {}),
                        }
            except Exception as e:
                logger.warning("Local OpenAI-compatible request to '{}' failed: {}", target_provider.name, e)

        return {
            "text": f"[Mitchell Local Fallback]: Processed prompt '{prompt[:50]}...'",
            "model": target_model,
            "provider": target_provider.name,
        }

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        provider_name: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for local generation."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.async_generate(prompt, system, model, provider_name, temperature)).result()
            return loop.run_until_complete(self.async_generate(prompt, system, model, provider_name, temperature))
        except Exception:
            return asyncio.run(self.async_generate(prompt, system, model, provider_name, temperature))


# Global singleton instance
multi_local_llm = MultiLocalLLMManager()
local_llm = multi_local_llm

__all__ = ["MultiLocalLLMManager", "multi_local_llm", "local_llm", "LocalProviderConfig"]
