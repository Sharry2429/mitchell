"""Tests for Active-Provider Fallback Chain Engine."""

import pytest
from mitchell.core.fallback_chains import (
    FAST_MODE_CHAIN,
    INTELLIGENT_MODE_CHAIN,
    NEVER_FAILS_MODE_CHAIN,
    CODING_MODE_CHAIN,
    AUDIO_STT_CHAIN,
    AUDIO_TTS_CHAIN,
    fallback_engine,
)


def test_chain_definitions_and_counts():
    """Verify exact chain structure and active provider presence."""
    assert len(FAST_MODE_CHAIN) == 30
    assert len(INTELLIGENT_MODE_CHAIN) == 33
    assert len(NEVER_FAILS_MODE_CHAIN) == 50
    assert len(CODING_MODE_CHAIN) == 19
    assert len(AUDIO_STT_CHAIN) == 2
    assert len(AUDIO_TTS_CHAIN) == 2

    # Verify providers present in chains
    for chain in (FAST_MODE_CHAIN, INTELLIGENT_MODE_CHAIN, NEVER_FAILS_MODE_CHAIN, CODING_MODE_CHAIN):
        providers = {p for p, _ in chain}
        assert "groq" in providers
        assert "omniroute" in providers
        assert "nvidia" in providers
        assert "openrouter" in providers
        # Custom gemini excluded
        assert "gemini" not in providers


@pytest.mark.anyio
async def test_fallback_chain_offline_floor():
    """Test full fallback sequence when all endpoints fail or time out."""
    messages = [
        {"role": "system", "content": "You are Mitchell."},
        {"role": "user", "content": "Ping test."},
    ]
    res = await fallback_engine.execute(
        messages=messages,
        mode="fast",
        timeout=0.01,  # Fast timeout to simulate network failures
    )
    assert res.content is not None
    assert res.attempts_made > 0
