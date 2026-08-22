"""Local offline LLM provider support (Ollama / vLLM) for Mitchell."""

import os
from typing import Any, Dict, List, Optional

from mitchell.core.logging import logger

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class LocalLLMProvider:
    """Zero-cost local offline LLM provider using Ollama / local OpenAI-compatible endpoints."""

    def __init__(self, base_url: Optional[str] = None, default_model: str = "llama3.2") -> None:
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_model = default_model

    def is_available(self) -> bool:
        """Check if local Ollama server is running and responding."""
        if not HAS_REQUESTS:
            return False
        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            return res.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> List[str]:
        """Fetch list of locally installed Ollama models."""
        if not HAS_REQUESTS:
            return []
        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.debug("Failed to list local models: {}", e)
        return []

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate a completion from the local Ollama instance."""
        target_model = model or self.default_model
        if not HAS_REQUESTS:
            return {"text": f"[Offline Mock Response]: {prompt[:50]}", "model": target_model}

        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        try:
            res = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=45)
            if res.status_code == 200:
                data = res.json()
                return {
                    "text": data.get("response", "").strip(),
                    "model": target_model,
                    "total_duration": data.get("total_duration", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                }
            else:
                logger.warning("Local LLM error {}: {}", res.status_code, res.text[:200])
        except Exception as e:
            logger.debug("Local LLM request failed: {}", e)

        # Fallback offline simulation string if Ollama is not actively running
        return {
            "text": f"[Mitchell Offline Response]: Processed prompt '{prompt[:40]}...'",
            "model": "offline-fallback",
        }


local_llm = LocalLLMProvider()

__all__ = ["LocalLLMProvider", "local_llm"]
