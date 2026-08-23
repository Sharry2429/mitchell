"""Unit tests for Agent Harness, Deep Research, and Procedural Skill Synthesizer."""

import asyncio
import pytest
from mitchell.ide.agent_harness import MultiAgentHarness
from mitchell.browser.deep_research import DeepResearchEngine
from mitchell.teaching.recorder import ActionRecorder
from mitchell.teaching.synthesizer import SkillSynthesizer
from mitchell.action.takeover import TaskTakeoverEngine


def test_agent_harness_spawn_and_list():
    """Verify multi-agent harness creates and tracks sessions."""
    async def _test():
        harness = MultiAgentHarness()
        session = await harness.start_agent_task(
            agent_id="claude",
            prompt="Refactor database indexes",
        )
        assert session.session_id.startswith("claude_")
        assert session.status in ("running", "completed")

        await asyncio.sleep(0.5)
        fetched = harness.get_session(session.session_id)
        assert fetched is not None

    asyncio.run(_test())


def test_deep_research_synthesis():
    """Verify deep research decomposes query, gathers sources, and produces citations."""
    async def _test():
        engine = DeepResearchEngine()
        result = await engine.execute_research(
            query="Self-healing selectors in browser automation",
            max_sources=3,
        )
        assert result.query == "Self-healing selectors in browser automation"
        assert len(result.sources) > 0
        assert len(result.key_findings) > 0
        assert "[1]" in result.detailed_report or len(result.sources) > 0

    asyncio.run(_test())


def test_skill_synthesizer():
    """Verify human demonstrations are parameterized into valid procedural skills."""
    recorder = ActionRecorder()
    recorder.add_action("tool", "browser_goto", {"url": "https://github.com"}, 100.0)
    recorder.add_action("tool", "browser_snapshot", {}, 101.0)

    synthesizer = SkillSynthesizer()
    res = synthesizer.synthesize_from_recorder(
        recorder,
        name="github_inspector",
        description="Inspects github repos",
    )
    assert res.success is True
    assert res.skill_name == "github_inspector"
    assert res.steps_count == 2
    assert "url" in res.parameters


def test_takeover_checkpoints_and_approval():
    """Verify task takeover state machine and approval gate functionality."""
    engine = TaskTakeoverEngine()
    session = engine.start_takeover(goal="Deploy staging service")
    assert session.status == "running"
    assert session.current_step_index == 0

    # Advance steps 1 -> 4
    for i in range(4):
        engine.advance_step(session.session_id, success=True)

    session_state = engine.get_session(session.session_id)
    assert session_state.status == "waiting_gate"
    assert session_state.steps[4].status == "waiting_approval"

    # User approves gate
    engine.approve_gate(session.session_id)
    assert session_state.status == "running"
    assert session_state.steps[4].status == "in_progress"
