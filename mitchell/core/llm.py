"""Multi-Model Cloud Router with provider cascade, free-tier prioritization, streaming, and fallback.

Integrates with the ProviderRegistry for dynamic provider management, health tracking,
and automatic cascade fallback. Supports Groq, NVIDIA NIM, OpenRouter, DeepSeek,
xAI (Grok), OpenAI, Anthropic, and Google Gemini.
"""

import asyncio
import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.cost import cost_tracker
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.core.prompts import (
    MITCHELL_CORE_SYSTEM_PROMPT,
    MITCHELL_PLANNER_SYSTEM_PROMPT,
    MITCHELL_CRITIC_SYSTEM_PROMPT,
    MITCHELL_COUNCIL_SYSTEM_PROMPT,
    MITCHELL_SYNTHESIS_SYSTEM_PROMPT,
    build_dynamic_system_prompt,
)
from mitchell.core.providers import ProviderEndpoint, provider_registry

KARPATHY_SYSTEM_PROMPT = MITCHELL_CORE_SYSTEM_PROMPT


class LLMResponse(BaseModel):
    """Structured response from LLM inference."""

    content: str
    model: str
    provider: str = "unknown"
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_inr: float
    cost_usd: float
    latency_ms: float = 0.0
    is_mock: bool = False
    is_free_tier: bool = False


class ModelRouter:
    """Routes inference requests to cloud models with automatic cascade fallback,
    free-tier prioritization, streaming support, and health tracking."""

    def __init__(self) -> None:
        self.default_model = "llama-3.3-70b-versatile"  # Default to Groq free tier
        self.cost_tracker = cost_tracker
        self.registry = provider_registry

    def select_best_model(self, task_type: str = "general", complexity: str = "medium") -> str:
        """Self-model aware model selection optimizing for cost and reasoning capacity."""
        provider, model, _ = self.registry.select_provider(
            task_type=task_type, complexity=complexity
        )
        if model:
            return model

        # Legacy fallback
        if complexity in ("high", "high_stakes") or task_type in ("planning", "council", "critic"):
            return "grok-2"
        elif task_type in ("browser", "scraping", "parsing"):
            return "deepseek-chat"
        elif task_type in ("windows", "android", "device"):
            return "gpt-4o-mini"
        return "llama-3.3-70b-versatile"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
        purpose: str = "general",
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> LLMResponse:
        """Generate response via provider cascade with automatic fallback.

        Tries providers in cascade order (free-tier first), falling back
        through the chain on failure.
        """
        target_model = model or self.default_model
        sys_prompt = (system_prompt or KARPATHY_SYSTEM_PROMPT).strip()

        logger.debug("LLM Router: Generating with model '{}' for purpose '{}'", target_model, purpose)

        # Build cascade of providers to try
        cascade = self._build_cascade(target_model)

        for provider, api_key, resolved_model in cascade:
            try:
                start_ms = time.time() * 1000
                res = await self._call_provider(
                    provider=provider,
                    api_key=api_key,
                    model=resolved_model,
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    temperature=temperature,
                    json_mode=json_mode and provider.supports_json_mode,
                    max_tokens=max_tokens,
                )
                if res:
                    latency_ms = time.time() * 1000 - start_ms
                    self.registry.record_success(
                        provider.name, latency_ms, res["prompt_tokens"] + res["completion_tokens"]
                    )
                    rec = self.cost_tracker.record_usage(
                        model=res["model"],
                        prompt_tokens=res["prompt_tokens"],
                        completion_tokens=res["completion_tokens"],
                        purpose=purpose,
                    )
                    return LLMResponse(
                        content=res["content"],
                        model=res["model"],
                        provider=provider.name,
                        prompt_tokens=res["prompt_tokens"],
                        completion_tokens=res["completion_tokens"],
                        total_tokens=rec.total_tokens,
                        cost_inr=rec.cost_inr,
                        cost_usd=rec.cost_usd,
                        latency_ms=round(latency_ms, 1),
                        is_mock=False,
                        is_free_tier=provider.is_free_tier,
                    )
            except Exception as e:
                self.registry.record_failure(provider.name, str(e))
                logger.warning(
                    "Provider '{}' failed for model '{}': {}. Trying next in cascade...",
                    provider.name, resolved_model, e,
                )
                continue

        # All providers failed — heuristic fallback
        logger.warning("All providers exhausted, using heuristic fallback")
        return self._heuristic_fallback(prompt, sys_prompt, target_model, json_mode, purpose)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        purpose: str = "general",
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens from the best available provider.

        Yields content chunks as they arrive. Falls back through cascade on failure.
        """
        target_model = model or self.default_model
        sys_prompt = (system_prompt or KARPATHY_SYSTEM_PROMPT).strip()
        cascade = self._build_cascade(target_model)

        for provider, api_key, resolved_model in cascade:
            if not provider.supports_streaming:
                continue
            try:
                start_ms = time.time() * 1000
                total_content = ""
                total_prompt_tokens = 0
                total_completion_tokens = 0

                async for chunk in self._stream_provider(
                    provider=provider,
                    api_key=api_key,
                    model=resolved_model,
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    total_content += chunk
                    total_completion_tokens += 1  # Approximate
                    yield chunk

                latency_ms = time.time() * 1000 - start_ms
                total_prompt_tokens = max(10, len(prompt.split()) * 2)
                self.registry.record_success(
                    provider.name, latency_ms, total_prompt_tokens + total_completion_tokens
                )
                self.cost_tracker.record_usage(
                    model=resolved_model,
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                    purpose=purpose,
                )
                return  # Successfully streamed
            except Exception as e:
                self.registry.record_failure(provider.name, str(e))
                logger.warning("Stream failed for provider '{}': {}", provider.name, e)
                continue

        # Fallback: yield heuristic response as single chunk
        fallback = self._heuristic_fallback(prompt, sys_prompt, target_model, False, purpose)
        yield fallback.content

    def _build_cascade(
        self, requested_model: str
    ) -> List[tuple[ProviderEndpoint, str, str]]:
        """Build ordered cascade of (provider, api_key, model) to try."""
        result: List[tuple[ProviderEndpoint, str, str]] = []

        # First: try to find the exact requested model
        for name, prov in provider_registry._providers.items():
            if not prov.enabled:
                continue
            if requested_model in prov.models:
                api_key = self.registry.get_api_key(name)
                if api_key:
                    health = self.registry.get_health(name)
                    if health and health.is_healthy:
                        result.append((prov, api_key, requested_model))

        # Then: add all providers in cascade order with their best model
        for prov, api_key in self.registry.get_cascade_order(prefer_free=settings.free_tier_first):
            best_model = prov.models[0] if prov.models else requested_model
            entry = (prov, api_key, best_model)
            if entry not in result:
                result.append(entry)

        return result

    async def _call_provider(
        self,
        provider: ProviderEndpoint,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        json_mode: bool,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make OpenAI-compatible API call to a provider."""
        url = f"{provider.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Add provider-specific headers
        headers.update(provider.headers_template)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=settings.provider_timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return {
                    "content": content,
                    "model": model,
                    "prompt_tokens": usage.get("prompt_tokens", len(prompt) // 4),
                    "completion_tokens": usage.get("completion_tokens", len(content) // 4),
                }
            else:
                error_text = resp.text[:200]
                raise RuntimeError(f"HTTP {resp.status_code}: {error_text}")

    async def _stream_provider(
        self,
        provider: ProviderEndpoint,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from an OpenAI-compatible provider endpoint."""
        url = f"{provider.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        headers.update(provider.headers_template)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=settings.provider_timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    raise RuntimeError(f"HTTP {resp.status_code}: {error_text[:200]}")

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    def _heuristic_fallback(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        json_mode: bool,
        purpose: str,
    ) -> LLMResponse:
        """Heuristic response generator when working offline or without external API keys."""
        prompt_tokens = max(10, len(prompt.split()) * 2)
        completion_tokens = 45

        if json_mode:
            content = json.dumps({
                "status": "planned",
                "summary": f"Analyzed goal: {prompt[:80]}",
                "principles_applied": ["Think Before Acting", "Simplicity First"],
                "recommendation": "Execute planned subtasks sequentially",
            })
        else:
            content = f"[Mitchell Engine ({model})]: Evaluated task with Karpathy Principles. Ready to coordinate workers for: {prompt}"

        rec = self.cost_tracker.record_usage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            purpose=purpose,
        )

        return LLMResponse(
            content=content,
            model=model,
            provider="heuristic",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=rec.total_tokens,
            cost_inr=rec.cost_inr,
            cost_usd=rec.cost_usd,
            is_mock=True,
            is_free_tier=True,
        )

    # ── Live Switching API ─────────────────────────────────────────────────

    def set_default_model(self, model: str) -> None:
        """Switch the default model at runtime."""
        self.default_model = model
        logger.info("Default model switched to '{}'", model)

    def get_status(self) -> Dict[str, Any]:
        """Get router status for Studio UI."""
        return {
            "default_model": self.default_model,
            "providers": self.registry.get_state(),
            "cost": self.cost_tracker.get_summary(),
        }


model_router = ModelRouter()

__all__ = [
    "ModelRouter",
    "model_router",
    "LLMResponse",
    "KARPATHY_SYSTEM_PROMPT",
    "MITCHELL_CORE_SYSTEM_PROMPT",
    "MITCHELL_PLANNER_SYSTEM_PROMPT",
    "MITCHELL_CRITIC_SYSTEM_PROMPT",
    "MITCHELL_COUNCIL_SYSTEM_PROMPT",
    "MITCHELL_SYNTHESIS_SYSTEM_PROMPT",
    "build_dynamic_system_prompt",
]
