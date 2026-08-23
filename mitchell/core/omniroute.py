"""OmniRoute — Unified Multi-Provider Gateway & .env Provider Auto-Loader for Mitchell.

Features:
- Automatic detection and connection to external OmniRoute instances (e.g., http://localhost:8000 / http://localhost:8080)
- In-process high-velocity fallback router when external daemon is offline
- Dynamic .env key loader: auto-discovers and binds all provider keys without prefixes (GROQ_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, DEEPSEEK_API_KEY, XAI_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY)
- Live health monitoring, latency tracking, and automatic cascade fallback
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from mitchell.core.logging import logger

try:
    import dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


class OmniRouteStatus(BaseModel):
    """Status snapshot of the OmniRoute gateway."""

    is_external_running: bool = False
    external_url: str = "http://localhost:8000"
    mode: str = "in_process"  # "external_proxy" | "in_process"
    configured_providers: List[str] = Field(default_factory=list)
    total_providers_available: int = 0
    active_cascade: List[str] = Field(default_factory=list)
    ping_latency_ms: float = 0.0


class OmniRouteManager:
    """Manages OmniRoute provider gateway and auto-loads all environment keys."""

    def __init__(self, external_url: Optional[str] = None) -> None:
        self.external_url = (external_url or os.environ.get("OMNIROUTE_URL", "http://localhost:8000")).rstrip("/")
        self.is_external = False
        self.load_env_keys()

    def load_env_keys(self, env_path: Optional[str | Path] = None) -> Dict[str, bool]:
        """Load API keys from .env file directly into os.environ and return status dict."""
        if HAS_DOTENV:
            target_env = Path(env_path) if env_path else Path(".env")
            if target_env.exists():
                dotenv.load_dotenv(dotenv_path=target_env, override=True)
                logger.info("OmniRoute: Loaded environment keys from '{}'", target_env)

        # Standard cloud provider key mapping
        key_map = {
            "groq": ["GROQ_API_KEY", "MITCHELL_GROQ_API_KEY"],
            "openai": ["OPENAI_API_KEY", "MITCHELL_OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY", "MITCHELL_ANTHROPIC_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "MITCHELL_GEMINI_API_KEY"],
            "deepseek": ["DEEPSEEK_API_KEY", "MITCHELL_DEEPSEEK_API_KEY"],
            "xai": ["XAI_API_KEY", "GROK_API_KEY", "MITCHELL_XAI_API_KEY"],
            "nvidia_nim": ["NVIDIA_NIM_API_KEY", "NVIDIA_API_KEY", "MITCHELL_NVIDIA_NIM_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY", "MITCHELL_OPENROUTER_API_KEY"],
        }

        configured: Dict[str, bool] = {}
        for provider, env_vars in key_map.items():
            found = False
            for v in env_vars:
                val = os.environ.get(v, "").strip()
                if val:
                    found = True
                    # Ensure primary env var is set
                    os.environ[env_vars[0]] = val
                    break
            configured[provider] = found

        return configured

    async def check_external_omniroute(self) -> bool:
        """Check if an external OmniRoute daemon is running."""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.external_url}/health")
                if res.status_code == 200:
                    self.is_external = True
                    logger.info("OmniRoute: Connected to external proxy at {}", self.external_url)
                    return True
        except Exception:
            pass

        self.is_external = False
        return False

    def get_status(self) -> OmniRouteStatus:
        """Return comprehensive status of the OmniRoute gateway."""
        configured_keys = self.load_env_keys()
        active_list = [k for k, v in configured_keys.items() if v]

        return OmniRouteStatus(
            is_external_running=self.is_external,
            external_url=self.external_url,
            mode="external_proxy" if self.is_external else "in_process",
            configured_providers=active_list,
            total_providers_available=len(active_list),
            active_cascade=["groq", "nvidia_nim", "openrouter", "deepseek", "openai", "anthropic", "gemini", "local"],
        )

    async def route_inference(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Route inference via external OmniRoute if active, else through in-process ModelRouter."""
        # 1. External OmniRoute proxy path
        if self.is_external:
            try:
                payload = {
                    "messages": messages,
                    "model": model or "auto",
                    "temperature": temperature,
                    "stream": stream,
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(f"{self.external_url}/v1/chat/completions", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        content = choices[0].get("message", {}).get("content", "") if choices else ""
                        return {
                            "content": content,
                            "model": data.get("model", model or "omniroute"),
                            "provider": "omniroute_external",
                            "usage": data.get("usage", {}),
                        }
            except Exception as e:
                logger.warning("External OmniRoute failed, falling back to in-process router: {}", e)

        # 2. In-Process Cascade Router
        from mitchell.core.llm import model_router
        prompt = messages[-1].get("content", "") if messages else ""
        sys_prompt = next((m.get("content") for m in messages if m.get("role") == "system"), None)

        res = await model_router.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            model=model,
            temperature=temperature,
        )
        return {
            "content": res.content,
            "model": res.model,
            "provider": res.provider,
            "cost_inr": res.cost_inr,
            "cost_usd": res.cost_usd,
        }


# Global singleton instance
omniroute = OmniRouteManager()

__all__ = ["OmniRouteManager", "omniroute", "OmniRouteStatus"]
