"""Deep Web Research tools for Mitchell ToolRegistry."""

import asyncio
from typing import Optional
from mitchell.browser.researcher import deep_researcher
from mitchell.tools.registry import Tool


def deep_web_research(topic: str) -> str:
    """Perform autonomous deep web research across online sources and synthesize a briefing."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                report = pool.submit(asyncio.run, deep_researcher.research(topic=topic)).result()
        else:
            report = loop.run_until_complete(deep_researcher.research(topic=topic))
    except Exception:
        report = asyncio.run(deep_researcher.research(topic=topic))

    lines = [
        f"=== Deep Research Report: {report.topic} ===",
        f"Summary: {report.summary}",
        f"Key Findings ({len(report.key_findings)}):",
    ]
    for kf in report.key_findings:
        lines.append(f"  • {kf}")
    lines.append(f"Sources Inspected: {len(report.sources)}")
    for s in report.sources:
        lines.append(f"  - {s.url} ({'✓' if s.success else '✗'})")
    return "\n".join(lines)


research_tool = Tool(
    name="deep_web_research",
    description="Autonomously research a topic across multiple web sources, extracting excerpts and synthesizing findings.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Research topic or question to investigate"}
        },
        "required": ["topic"],
    },
    function=deep_web_research,
)

TOOLS = [research_tool]
