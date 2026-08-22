"""Automated benchmark runner and performance scorecard generator."""

import time
from typing import Any, Dict, List, Optional

from mitchell.benchmark.scenarios import BENCHMARK_SUITE, BenchmarkScenario
from mitchell.core.logging import logger
from mitchell.manager import Manager


class BenchmarkScorecard:
    """Stores and formats evaluation metrics."""

    def __init__(self) -> None:
        self.results: List[Dict[str, Any]] = []

    def add_result(
        self,
        scenario: BenchmarkScenario,
        passed: bool,
        duration_s: float,
        output_snippet: str,
        error: Optional[str] = None,
    ) -> None:
        self.results.append({
            "id": scenario.id,
            "title": scenario.title,
            "domain": scenario.domain,
            "difficulty": scenario.difficulty,
            "passed": passed,
            "duration_s": round(duration_s, 2),
            "output_snippet": output_snippet[:120],
            "error": error,
        })

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        avg_lat = sum(r["duration_s"] for r in self.results) / max(total, 1)

        return {
            "total_scenarios": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate_pct": round((passed / max(total, 1)) * 100, 1),
            "avg_latency_s": round(avg_lat, 2),
            "results": self.results,
        }

    def generate_markdown_report(self) -> str:
        """Format a rich markdown leaderboard summary."""
        summary = self.get_summary()
        lines = [
            "# 🏆 Mitchell Autonomous Agent Benchmark Scorecard",
            "",
            f"- **Overall Pass Rate:** {summary['pass_rate_pct']}% ({summary['passed']}/{summary['total_scenarios']})",
            f"- **Average Latency:** {summary['avg_latency_s']}s",
            "",
            "| Scenario ID | Domain | Difficulty | Status | Latency (s) |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for r in self.results:
            status_badge = "✅ PASSED" if r["passed"] else "❌ FAILED"
            lines.append(f"| `{r['id']}` | {r['domain']} | {r['difficulty']} | {status_badge} | {r['duration_s']}s |")

        return "\n".join(lines)


class BenchmarkRunner:
    """Executes the standardized benchmark suite against Mitchell's Manager loop."""

    def __init__(self, manager_instance: Optional[Manager] = None) -> None:
        self.manager = manager_instance or Manager()

    def run_suite(self, scenarios: Optional[List[BenchmarkScenario]] = None) -> BenchmarkScorecard:
        """Run all designated benchmark scenarios and return the scorecard."""
        target_scenarios = scenarios or BENCHMARK_SUITE
        scorecard = BenchmarkScorecard()

        logger.info("BenchmarkRunner: Starting execution of {} scenarios...", len(target_scenarios))

        for sc in target_scenarios:
            start_ts = time.time()
            try:
                out = self.manager.run(sc.goal)
                duration = time.time() - start_ts
                passed = bool(out) and not str(out).startswith("Plan rejected")
                scorecard.add_result(
                    scenario=sc,
                    passed=passed,
                    duration_s=duration,
                    output_snippet=str(out),
                )
            except Exception as e:
                duration = time.time() - start_ts
                logger.error("Benchmark scenario '{}' crashed: {}", sc.id, e)
                scorecard.add_result(
                    scenario=sc,
                    passed=False,
                    duration_s=duration,
                    output_snippet="",
                    error=str(e),
                )

        return scorecard


benchmark_runner = BenchmarkRunner()

__all__ = ["BenchmarkRunner", "BenchmarkScorecard", "benchmark_runner"]
