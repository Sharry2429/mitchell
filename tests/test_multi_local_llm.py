"""Tests for Multi-Local LLM Provider Engine."""

import pytest
from mitchell.core.local_llm import MultiLocalLLMManager, LocalProviderConfig


def test_multi_local_llm_registry():
    """Test registering, retrieving, and removing multiple local providers."""
    mgr = MultiLocalLLMManager()

    # Verify default templates are loaded
    providers = mgr.list_providers()
    names = [p["name"] for p in providers]
    assert "ollama" in names
    assert "lmstudio" in names
    assert "vllm" in names
    assert "localai" in names

    # Add custom local provider
    custom = mgr.add_provider(
        name="gpu_cluster_lan",
        display_name="LAN GPU vLLM Server",
        provider_type="openai_compatible",
        base_url="http://192.168.1.150:8000/v1",
        default_model="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    )
    assert custom.name == "gpu_cluster_lan"
    assert mgr.get_provider("gpu_cluster_lan") is not None

    # Remove custom provider
    removed = mgr.remove_provider("gpu_cluster_lan")
    assert removed is True
    assert mgr.get_provider("gpu_cluster_lan") is None


@pytest.mark.anyio
async def test_multi_local_llm_fallback_generation():
    """Test local generation fallback when server is offline."""
    mgr = MultiLocalLLMManager()
    res = await mgr.async_generate(prompt="What is the capital of France?", provider_name="ollama")
    assert "text" in res
    assert "model" in res
    assert res["provider"] == "ollama" or res["provider"] == "mock"
