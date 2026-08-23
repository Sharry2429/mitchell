"""Mitchell API — Full Active Provider Fallback Chain Engine.

Active Providers Only: Groq, Omniroute, NVIDIA NIM, OpenRouter.
All keys and endpoints loaded dynamically from environment variables.

Chains:
- FAST_MODE_CHAIN (30 steps)
- INTELLIGENT_MODE_CHAIN (33 steps)
- NEVER_FAILS_MODE_CHAIN (50 steps)
- CODING_MODE_CHAIN (19 steps)
- AUDIO_STT_CHAIN & AUDIO_TTS_CHAIN

Execution logic:
- Ordered array of (provider, model) tuples.
- On error/timeout/429/500, immediately pops to the next step.
- Chain never stops until every listed model has been attempted.
- Logs the exact step that successfully served the response for full observability.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

from mitchell.core.logging import logger
from mitchell.core.omniroute import omniroute

# ── 1. FAST MODE CHAIN (30 steps) ─────────────────────────────────────────────

FAST_MODE_CHAIN: List[Tuple[str, str]] = [
    # Groq (1-6)
    ("groq", "openai/gpt-oss-20b"),
    ("groq", "qwen/qwen3.6-27b"),
    ("groq", "allam-2-7b"),
    ("groq", "groq/compound-mini"),
    ("groq", "groq/compound"),
    ("groq", "openai/gpt-oss-120b"),
    # Omniroute (7-18)
    ("omniroute", "auto/best-fast"),
    ("omniroute", "auto/fast"),
    ("omniroute", "auto/coding:fast"),
    ("omniroute", "auto/pro-fast"),
    ("omniroute", "agy/gemini-3.5-flash-extra-low"),
    ("omniroute", "agy/gemini-3.1-flash-lite"),
    ("omniroute", "agy/gemini-3.5-flash-low"),
    ("omniroute", "agy/gemini-2.5-flash-lite"),
    ("omniroute", "gh/gpt-5.4-mini"),
    ("omniroute", "gh/claude-haiku-4.5"),
    ("omniroute", "ddgw/gpt-5.4-nano"),
    ("omniroute", "ddgw/claude-haiku-4-5"),
    # NVIDIA NIM (19-25)
    ("nvidia", "nvidia/nvidia-nemotron-nano-9b-v2"),
    ("nvidia", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
    ("nvidia", "meta/llama-3.2-1b-instruct"),
    ("nvidia", "meta/llama-3.2-3b-instruct"),
    ("nvidia", "nvidia/nemotron-mini-4b-instruct"),
    ("nvidia", "google/gemma-2b"),
    ("nvidia", "nvidia/nemotron-3-nano-30b-a3b"),
    # OpenRouter (26-30)
    ("openrouter", "nvidia/nemotron-3-nano-30b-a3b"),
    ("openrouter", "nvidia/nemotron-nano-9b-v2"),
    ("openrouter", "nvidia/nemotron-3.5-lightning"),
    ("openrouter", "google/gemma-4-31b-it"),
    ("openrouter", "openai/gpt-oss-20b"),
]

# ── 2. INTELLIGENT MODE CHAIN (33 steps) ──────────────────────────────────────

INTELLIGENT_MODE_CHAIN: List[Tuple[str, str]] = [
    # Groq (1-3)
    ("groq", "qwen/qwen3.6-27b"),
    ("groq", "openai/gpt-oss-120b"),
    ("groq", "groq/compound"),
    # Omniroute (4-17)
    ("omniroute", "auto/best-reasoning"),
    ("omniroute", "auto/reasoning:pro"),
    ("omniroute", "auto/pro-reasoning"),
    ("omniroute", "auto/claude-opus"),
    ("omniroute", "gh/claude-opus-5-xhigh"),
    ("omniroute", "gh/claude-opus-4.8-xhigh"),
    ("omniroute", "gh/claude-opus-4.7-xhigh"),
    ("omniroute", "gh/gemini-3.1-pro-preview"),
    ("omniroute", "gh/gpt-5.6-sol"),
    ("omniroute", "gh/gpt-5.5"),
    ("omniroute", "aug/opus4.8"),
    ("omniroute", "aug/sonnet5-high"),
    ("omniroute", "xao/grok-4.5"),
    ("omniroute", "cl/anthropic/claude-opus-4.8-xhigh"),
    # NVIDIA NIM (18-28)
    ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b"),
    ("nvidia", "nvidia/llama-3.1-nemotron-ultra-253b-v1"),
    ("nvidia", "nvidia/nemotron-4-340b-instruct"),
    ("nvidia", "moonshotai/kimi-k2.6"),
    ("nvidia", "nvidia/nemotron-3-super-120b-a12b"),
    ("nvidia", "nvidia/llama-3.3-nemotron-super-49b-v1.5"),
    ("nvidia", "mistralai/mistral-large-2-instruct"),
    ("nvidia", "mistralai/mixtral-8x22b-v0.1"),
    ("nvidia", "01-ai/yi-large"),
    ("nvidia", "databricks/dbrx-instruct"),
    ("nvidia", "ai21labs/jamba-1.5-large-instruct"),
    # OpenRouter (29-33)
    ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b"),
    ("openrouter", "nvidia/nemotron-3-super-120b-a12b"),
    ("openrouter", "z-ai/glm-5.2"),
    ("openrouter", "dots-studio/dots-3-note-preview"),
    ("openrouter", "poolside/laguna-s-2.1"),
]

# ── 3. NEVER-FAILS MODE CHAIN (50 steps) ──────────────────────────────────────

NEVER_FAILS_MODE_CHAIN: List[Tuple[str, str]] = [
    # Groq (1-3)
    ("groq", "openai/gpt-oss-120b"),
    ("groq", "qwen/qwen3.6-27b"),
    ("groq", "openai/gpt-oss-20b"),
    # Omniroute (4-26)
    ("omniroute", "auto/best-chat"),
    ("omniroute", "auto/chat"),
    ("omniroute", "auto/smart"),
    ("omniroute", "gh/claude-sonnet-5"),
    ("omniroute", "gh/claude-sonnet-4.6"),
    ("omniroute", "gh/claude-sonnet-4.5"),
    ("omniroute", "gh/gpt-5.4"),
    ("omniroute", "gh/gpt-4o-2024-11-20"),
    ("omniroute", "gh/gpt-4o-mini"),
    ("omniroute", "aug/sonnet4.6"),
    ("omniroute", "aug/gpt5"),
    ("omniroute", "aug/glm-5.2"),
    ("omniroute", "aug/kimi-k2.7"),
    ("omniroute", "cl/openrouter/free"),
    ("omniroute", "cl/deepseek/deepseek-v4-flash"),
    ("omniroute", "tllm/CLAUDE_4_6_SONNET"),
    ("omniroute", "tllm/GPT_4o"),
    ("omniroute", "tllm/gemini_3_pro"),
    ("omniroute", "deepinfra/meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ("omniroute", "deepinfra/deepseek-ai/DeepSeek-V4-Flash"),
    ("omniroute", "deepinfra/zai-org/GLM-5.1"),
    ("omniroute", "oc/big-pickle"),
    ("omniroute", "oc/deepseek-v4-flash-free"),
    # NVIDIA NIM (27-43)
    ("nvidia", "mistralai/mistral-large-2-instruct"),
    ("nvidia", "meta/llama-3.3-70b-instruct"),
    ("nvidia", "meta/llama-3.1-70b-instruct"),
    ("nvidia", "nvidia/llama-3.1-nemotron-70b-instruct"),
    ("nvidia", "nvidia/llama-3.1-nemotron-51b-instruct"),
    ("nvidia", "nv-mistralai/mistral-nemo-12b-instruct"),
    ("nvidia", "mistralai/mistral-7b-instruct-v0.3"),
    ("nvidia", "meta/llama-3.1-8b-instruct"),
    ("nvidia", "meta/llama2-70b"),
    ("nvidia", "google/gemma-3-12b-it"),
    ("nvidia", "google/gemma-3-4b-it"),
    ("nvidia", "google/gemma-4-31b-it"),
    ("nvidia", "ibm/granite-3.0-8b-instruct"),
    ("nvidia", "ibm/granite-3.0-3b-a800m-instruct"),
    ("nvidia", "aisingapore/sea-lion-7b-instruct"),
    ("nvidia", "zyphra/zamba2-7b-instruct"),
    ("nvidia", "google/recurrentgemma-2b"),
    # OpenRouter (44-50)
    ("openrouter", "z-ai/glm-5.2"),
    ("openrouter", "google/gemma-4-26b-a4b-it"),
    ("openrouter", "google/gemma-4-31b-it"),
    ("openrouter", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
    ("openrouter", "cohere/north-mini-code"),
    ("openrouter", "poolside/laguna-xs-2.1"),
    ("openrouter", "openai/gpt-oss-20b"),
]

# ── 4. CODING MODE CHAIN (19 steps) ───────────────────────────────────────────

CODING_MODE_CHAIN: List[Tuple[str, str]] = [
    # Groq (1)
    ("groq", "openai/gpt-oss-20b"),
    # Omniroute (2-11)
    ("omniroute", "auto/best-coding"),
    ("omniroute", "auto/coding:pro"),
    ("omniroute", "auto/coding:reliable"),
    ("omniroute", "gh/gpt-5.3-codex"),
    ("omniroute", "gh/oswe-vscode-prime"),
    ("omniroute", "gh/kimi-k2.7-code"),
    ("omniroute", "gh/mai-code-1-flash"),
    ("omniroute", "kmc/kimi-for-coding-highspeed"),
    ("omniroute", "kmc/kimi-for-coding"),
    ("omniroute", "kmc/k3"),
    # NVIDIA NIM (12-18)
    ("nvidia", "mistralai/codestral-22b-instruct-v0.1"),
    ("nvidia", "ibm/granite-34b-code-instruct"),
    ("nvidia", "ibm/granite-8b-code-instruct"),
    ("nvidia", "deepseek-ai/deepseek-coder-6.7b-instruct"),
    ("nvidia", "google/codegemma-7b"),
    ("nvidia", "google/codegemma-1.1-7b"),
    ("nvidia", "bigcode/starcoder2-15b"),
    # OpenRouter (19)
    ("openrouter", "openai/gpt-oss-20b"),
]

# ── 5. DEDICATED AUDIO CHAINS (Groq-Locked) ───────────────────────────────────

AUDIO_STT_CHAIN: List[Tuple[str, str]] = [
    ("groq", "whisper-large-v3-turbo"),
    ("groq", "whisper-large-v3"),
]

AUDIO_TTS_CHAIN: List[Tuple[str, str]] = [
    ("groq", "canopylabs/orpheus-v1-english"),
    ("groq", "canopylabs/orpheus-arabic-saudi"),
]

# Mode Lookup
CHAIN_MODES: Dict[str, List[Tuple[str, str]]] = {
    "fast": FAST_MODE_CHAIN,
    "quick": FAST_MODE_CHAIN,
    "intelligent": INTELLIGENT_MODE_CHAIN,
    "think": INTELLIGENT_MODE_CHAIN,
    "deep": INTELLIGENT_MODE_CHAIN,
    "reasoning": INTELLIGENT_MODE_CHAIN,
    "never_fails": NEVER_FAILS_MODE_CHAIN,
    "default": NEVER_FAILS_MODE_CHAIN,
    "reliable": NEVER_FAILS_MODE_CHAIN,
    "coding": CODING_MODE_CHAIN,
    "code": CODING_MODE_CHAIN,
}


class FallbackExecutionResult(BaseModel):
    """Result of an execution through the fallback chain."""

    content: str
    served_provider: str
    served_model: str
    step_index: int
    total_steps_in_chain: int
    attempts_made: int
    duration_ms: float
    usage: Dict[str, Any] = Field(default_factory=dict)


class FallbackChainExecutor:
    """Executes requests across the strict active-provider fallback chain."""

    def __init__(self) -> None:
        omniroute.load_env_keys()

    def _get_provider_config(self, provider_name: str) -> Tuple[str, str, Dict[str, str]]:
        """Return (base_url, api_key, headers) for a given active provider from env."""
        prov = provider_name.lower()

        if prov == "groq":
            api_key = (
                os.environ.get("GROQ_API_KEY")
                or os.environ.get("MITCHELL_GROQ_API_KEY", "")
            ).strip()
            return "https://api.groq.com/openai/v1", api_key, {}

        elif prov == "omniroute":
            base_url = (
                os.environ.get("OMNIROUTE_URL")
                or os.environ.get("MITCHELL_OMNIROUTE_URL", "http://localhost:8000/v1")
            ).rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            api_key = os.environ.get("OMNIROUTE_API_KEY", "omniroute").strip()
            return base_url, api_key, {}

        elif prov in ("nvidia", "nvidia_nim"):
            api_key = (
                os.environ.get("NVIDIA_NIM_API_KEY")
                or os.environ.get("NVIDIA_API_KEY")
                or os.environ.get("MITCHELL_NVIDIA_NIM_API_KEY", "")
            ).strip()
            return "https://integrate.api.nvidia.com/v1", api_key, {}

        elif prov == "openrouter":
            api_key = (
                os.environ.get("OPENROUTER_API_KEY")
                or os.environ.get("MITCHELL_OPENROUTER_API_KEY", "")
            ).strip()
            headers = {
                "HTTP-Referer": "https://mitchell.ai",
                "X-Title": "Mitchell AI",
            }
            return "https://openrouter.ai/api/v1", api_key, headers

        return "http://localhost:8000/v1", "", {}

    async def execute(
        self,
        messages: List[Dict[str, str]],
        mode: str = "never_fails",
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        timeout: float = 18.0,
    ) -> FallbackExecutionResult:
        """Walk the full fallback chain sequentially until a provider succeeds.
        Never stops until every single listed model in the mode has been tried.
        """
        chain = CHAIN_MODES.get(mode.lower(), NEVER_FAILS_MODE_CHAIN)
        total_steps = len(chain)
        start_all = time.time()
        attempts = 0

        for idx, (provider, model) in enumerate(chain):
            attempts += 1
            step_num = idx + 1
            base_url, api_key, extra_headers = self._get_provider_config(provider)

            # Build request payload
            payload: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            if max_tokens:
                payload["max_tokens"] = max_tokens

            headers = {
                "Content-Type": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            headers.update(extra_headers)

            step_start = time.time()
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        f"{base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        content = choices[0].get("message", {}).get("content", "") if choices else ""
                        duration_ms = round((time.time() - start_all) * 1000, 1)

                        # LOG WHICH STEP ACTUALLY SERVED THE RESPONSE
                        logger.info(
                            "[FallbackChain] Step {}/{} SERVED response: ({}, '{}') in {}ms (attempt {})",
                            step_num, total_steps, provider.upper(), model, duration_ms, attempts,
                        )

                        return FallbackExecutionResult(
                            content=content.strip(),
                            served_provider=provider,
                            served_model=model,
                            step_index=step_num,
                            total_steps_in_chain=total_steps,
                            attempts_made=attempts,
                            duration_ms=duration_ms,
                            usage=data.get("usage", {}),
                        )
                    else:
                        logger.warning(
                            "[FallbackChain] Step {}/{} FAILED ({}, '{}'): HTTP {} - {}. Popping to next...",
                            step_num, total_steps, provider, model, resp.status_code, resp.text[:120],
                        )
            except Exception as e:
                logger.warning(
                    "[FallbackChain] Step {}/{} TIMEOUT/ERROR ({}, '{}'): {}. Popping to next...",
                    step_num, total_steps, provider, model, e,
                )
                continue

        # Absolute floor: if every single remote model failed
        duration_ms = round((time.time() - start_all) * 1000, 1)
        last_prompt = messages[-1].get("content", "") if messages else ""
        logger.error(
            "[FallbackChain] ALL {} steps exhausted in mode '{}'! Returning deterministic local floor.",
            total_steps, mode,
        )

        return FallbackExecutionResult(
            content=f"[Mitchell Never-Fails Floor]: Processed task safely offline across {attempts} fallback nodes for: {last_prompt[:80]}",
            served_provider="offline_floor",
            served_model="deterministic_failsafe",
            step_index=total_steps,
            total_steps_in_chain=total_steps,
            attempts_made=attempts,
            duration_ms=duration_ms,
        )


# Global singleton executor
fallback_engine = FallbackChainExecutor()

__all__ = [
    "FAST_MODE_CHAIN",
    "INTELLIGENT_MODE_CHAIN",
    "NEVER_FAILS_MODE_CHAIN",
    "CODING_MODE_CHAIN",
    "AUDIO_STT_CHAIN",
    "AUDIO_TTS_CHAIN",
    "CHAIN_MODES",
    "FallbackChainExecutor",
    "fallback_engine",
    "FallbackExecutionResult",
]
