"""Demo script testing Phase 4: Thinking Maturity, Multi-Model Router, Cost Tracker in INR, and LLM Council."""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mitchell.core.cost import cost_tracker
from mitchell.core.llm import model_router
from mitchell.hive import hive_router
from mitchell.manager.classifier import goal_classifier
from mitchell.manager.council import llm_council
from mitchell.manager.critic import plan_critic
from mitchell.manager.loop import Manager
from mitchell.manager.planner import task_planner

console = Console()


def run_phase4_demo() -> None:
    console.print(Panel("[bold green]Mitchell Phase 4: Thinking Maturity & Cloud Router Demo[/bold green]", border_style="cyan"))

    # 1. Token & Cost Tracker in INR (₹)
    console.print("\n[bold cyan]1. Token & Cost Tracker (INR / USD):[/bold cyan]")
    cost_tracker.record_usage(model="grok-2", prompt_tokens=1200, completion_tokens=350, purpose="planning")
    cost_tracker.record_usage(model="deepseek-chat", prompt_tokens=2500, completion_tokens=800, purpose="browser_subtask")
    summary = cost_tracker.get_summary()

    cost_table = Table(show_header=True, header_style="bold green")
    cost_table.add_column("Metric", style="cyan")
    cost_table.add_column("Value", style="white")
    for k, v in summary.items():
        cost_table.add_row(k, str(v))
    console.print(cost_table)

    # 2. Goal Classifier
    console.print("\n[bold cyan]2. Goal Classification & Complexity:[/bold cyan]")
    test_goal = "Open the browser, navigate to news.ycombinator.com, and summarize top stories"
    classification = goal_classifier.classify(test_goal)
    console.print(f"Goal: [white]{test_goal}[/white]")
    console.print(f"Domain: [yellow]{classification.domain}[/yellow] | Complexity: [magenta]{classification.complexity}[/magenta] | Target Agents: [cyan]{classification.target_agents}[/cyan]")

    # 3. Plan Synthesis (TaskGraph) & Critic Pass
    console.print("\n[bold cyan]3. Structured Plan Synthesis & Safety Critic:[/bold cyan]")
    plan = asyncio.run(task_planner.create_plan(test_goal, classification))
    console.print(f"Synthesized Plan [{plan.id}] with {len(plan.nodes)} subtasks:")
    for node in plan.nodes:
        console.print(f"  • [{node.target_agent}] {node.title} -> action: '{node.action}' (deps: {node.dependencies})")

    review = plan_critic.evaluate(plan)
    console.print(f"Critic Evaluation: Approved=[green]{review.approved}[/green] (Score: {review.score}, Safety: {review.safety_check_passed})")

    # 4. Selective LLM Council (High-Stakes Deliberation)
    console.print("\n[bold cyan]4. Selective LLM Council (High-Stakes Deliberation):[/bold cyan]")
    decision = asyncio.run(llm_council.deliberate(
        topic="Deploy database migration and purge stale user cache",
        proposed_action="Wipe cache partitions and rebuild indexes",
    ))
    console.print(f"Council Consensus: [bold green]{decision.consensus_decision}[/bold green]")
    for role, perspective in decision.perspectives.items():
        console.print(f"  [{role}]: [dim]{perspective}[/dim]")
    console.print(f"Chairman Summary: [cyan]{decision.chairman_summary}[/cyan]")

    # 5. Autoresearch Efficiency Agent
    console.print("\n[bold cyan]5. Autoresearch Efficiency Agent:[/bold cyan]")
    eff_res = hive_router.send_message("efficiency_worker", "Run prompt and cost audit", sender="demo_phase4")
    console.print(f"Audit Status: [green]{eff_res.get('message')}[/green]")
    console.print(f"Estimated Optimization: [yellow]{eff_res.get('latest_experiment', {}).get('efficiency_gain_estimated')}[/yellow]")

    # 6. End-to-End Manager Thinking Loop
    console.print("\n[bold cyan]6. End-to-End Manager Thinking Loop:[/bold cyan]")
    manager = Manager()
    response = manager.receive("self model")
    console.print(f"Manager Response:\n{response}")


if __name__ == "__main__":
    run_phase4_demo()
