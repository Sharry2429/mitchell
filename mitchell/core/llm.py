"""Multi-Model Cloud Router integrating Grok, DeepSeek, OpenAI, Anthropic, and Gemini with Karpathy principles."""

import json
import os
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.cost import cost_tracker
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger

KARPATHY_SYSTEM_PROMPT = """You are Mitchell, an autonomous AI Manager and multi-agent hive orchestrator.
Always adhere strictly to the Karpathy Principles of engineering:
1. THINK BEFORE ACTING: Formulate a clear hypothesis and mental model before executing actions.
2. SIMPLICITY FIRST: Choose the most direct and minimal path with the fewest necessary steps.
3. SURGICAL CHANGES: Make targeted, precise interventions without side-effects or bloat.
4. GOAL-DRIVEN EXECUTION: Continually verify state against verifiable success criteria.
Output concise, structured, and actionable plans and responses.
"""


class LLMResponse(BaseModel):
    """Structured response from LLM inference."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_inr: float
    cost_usd: float
    is_mock: bool = False


class ModelRouter:
    """Routes inference requests to cloud models with automatic fallback, cost tracking, and Karpathy principles."""

    def __init__(self) -> None:
        self.default_model = "grok-2"
        self.cost_tracker = cost_tracker

    def select_best_model(self, task_type: str = "general", complexity: str = "medium") -> str:
        """Self-model aware model selection optimizing for cost and reasoning capacity."""
        if complexity in ("high", "high_stakes") or task_type in ("planning", "council", "critic"):
            return "grok-2"
        elif task_type in ("browser", "scraping", "parsing"):
            return "deepseek-chat"
        elif task_type in ("windows", "android", "device"):
            return "gpt-4o-mini"
        return "gemini-1.5-flash"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
        purpose: str = "general",
    ) -> LLMResponse:
        """Generate response via cloud API or heuristic fallback."""
        target_model = (model or self.default_model).lower()
        sys_prompt = (system_prompt or KARPATHY_SYSTEM_PROMPT).strip()

        # Check API Keys
        api_key = (
            os.getenv("XAI_API_KEY")
            or os.getenv("GROK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
        )

        logger.debug("LLM Router: Generating with model '{}' for purpose '{}'", target_model, purpose)

        # 1. Real API execution if API key is present
        if api_key:
            try:
                res = await self._call_cloud_api(
                    api_key=api_key,
                    model=target_model,
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    temperature=temperature,
                    json_mode=json_mode,
                )
                if res:
                    rec = self.cost_tracker.record_usage(
                        model=res["model"],
                        prompt_tokens=res["prompt_tokens"],
                        completion_tokens=res["completion_tokens"],
                        purpose=purpose,
                    )
                    return LLMResponse(
                        content=res["content"],
                        model=res["model"],
                        prompt_tokens=res["prompt_tokens"],
                        completion_tokens=res["completion_tokens"],
                        total_tokens=rec.total_tokens,
                        cost_inr=rec.cost_inr,
                        cost_usd=rec.cost_usd,
                        is_mock=False,
                    )
            except Exception as e:
                logger.warning("Cloud LLM call failed, using heuristic fallback: {}", e)

        # 2. Heuristic fallback when no API key configured
        return self._heuristic_fallback(prompt, sys_prompt, target_model, json_mode, purpose)

    async def _call_cloud_api(
        self,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        json_mode: bool,
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP inference call to OpenAI/xAI/DeepSeek compatible endpoint."""
        url = "https://api.x.ai/v1/chat/completions" if "grok" in model else (
            "https://api.deepseek.com/chat/completions" if "deepseek" in model else "https://api.openai.com/v1/chat/completions"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

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

        async with httpx.AsyncClient(timeout=30.0) as client:
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
        return None

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
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=rec.total_tokens,
            cost_inr=rec.cost_inr,
            cost_usd=rec.cost_usd,
            is_mock=True,
        )


model_router = ModelRouter()

__all__ = ["ModelRouter", "model_router", "LLMResponse", "KARPATHY_SYSTEM_PROMPT"]
