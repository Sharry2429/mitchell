"""Studio and Benchmark tools for Mitchell ToolRegistry."""

import json
from typing import Any, Dict, Optional

from mitchell.benchmark.runner import benchmark_runner
from mitchell.benchmark.scenarios import BENCHMARK_SUITE
from mitchell.studio.server import studio_state
from mitchell.tools.registry import Tool


def tool_studio_get_state() -> str:
    """Retrieve full live snapshot of the Mitchell studio state (blackboard, cost, events)."""
    state = studio_state.get_full_state()
    return json.dumps(state, indent=2, default=str)


def tool_benchmark_run(domain: Optional[str] = None) -> str:
    """Run benchmark evaluation suite, optionally filtering by domain."""
    scenarios = BENCHMARK_SUITE
    if domain:
        scenarios = [s for s in BENCHMARK_SUITE if s.domain == domain]

    scorecard = benchmark_runner.run_suite(scenarios=scenarios)
    return scorecard.generate_markdown_report()


studio_state_tool = Tool(
    name="studio_get_live_state",
    description="Retrieve live snapshot of shared blackboard, cost tracker, and active event log.",
    parameters={"type": "object", "properties": {}},
    function=tool_studio_get_state,
)

benchmark_tool = Tool(
    name="benchmark_run_evaluation",
    description="Execute multi-agent benchmark evaluation suite and generate performance scorecard.",
    parameters={
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Optional domain filter: 'browser', 'windows', 'android', 'reasoning', 'vision'"}
        },
    },
    function=tool_benchmark_run,
)

TOOLS = [studio_state_tool, benchmark_tool]
