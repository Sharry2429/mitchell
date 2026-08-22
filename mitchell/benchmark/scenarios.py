"""Curated benchmark scenarios for evaluating Mitchell's autonomous capabilities."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class BenchmarkScenario(BaseModel):
    """A standardized autonomous challenge for agent evaluation."""

    id: str
    title: str
    domain: str  # "browser", "windows", "android", "reasoning", "vision"
    goal: str
    expected_output_type: str = "text"
    validation_fn_name: str = "default_validator"
    difficulty: str = "medium"  # "easy", "medium", "hard"


BENCHMARK_SUITE: List[BenchmarkScenario] = [
    BenchmarkScenario(
        id="bench_browser_research_01",
        title="Web Extraction & Multi-Source Synthesis",
        domain="browser",
        goal="Search and summarize the latest updates in Playwright 1.42 with verified citations.",
        difficulty="medium",
    ),
    BenchmarkScenario(
        id="bench_windows_mouse_02",
        title="Human Mouse Trajectory Generation",
        domain="windows",
        goal="Calculate a Bezier curve path from (100, 100) to (800, 600) with realistic human jitter.",
        difficulty="easy",
    ),
    BenchmarkScenario(
        id="bench_android_hierarchy_03",
        title="Wireless Android Touch & XML Hierarchy Dump",
        domain="android",
        goal="Dump Android UI hierarchy and locate the Search node by resource-id.",
        difficulty="medium",
    ),
    BenchmarkScenario(
        id="bench_hive_dag_planning_04",
        title="Multi-Node Task Graph Decomposition & Critic Pass",
        domain="reasoning",
        goal="Formulate a 3-node dependency graph to conduct deep web research, summarize in markdown, and audit for safety.",
        difficulty="hard",
    ),
    BenchmarkScenario(
        id="bench_vision_grounding_05",
        title="Multimodal Screen Parsing & Element Bounding Box",
        domain="vision",
        goal="Locate the submit button coordinates on a 1920x1080 screenshot canvas.",
        difficulty="medium",
    ),
]

__all__ = ["BenchmarkScenario", "BENCHMARK_SUITE"]
