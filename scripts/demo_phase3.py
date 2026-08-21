"""Demo script testing Phase 3: Full Memory + Skill System and Self-Model."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mitchell.core import event_log
from mitchell.manager import Manager
from mitchell.memory import (
    episodic_memory,
    long_term_memory,
    self_model,
    vector_store,
)
from mitchell.skills import skill_executor, skill_learner, skill_library

console = Console()


def run_phase3_demo() -> None:
    console.print(Panel("[bold green]Mitchell Phase 3: Full Memory + Skill System Demo[/bold green]", border_style="cyan"))

    # 1. Test Long-Term Memory (Factual & Preference Storage + Vector Search)
    console.print("\n[bold cyan]1. Long-Term Memory & Semantic RAG Search:[/bold cyan]")
    long_term_memory.remember(
        category="preferences",
        key="browser_preference",
        content="Always use dark mode and headless mode for routine background tasks",
    )
    long_term_memory.remember(
        category="project_context",
        key="active_repo",
        content="Mitchell project repository located at d:\\Mitchell",
    )
    matches = long_term_memory.search("What browser setting should I use?", top_k=2)
    console.print("RAG Search for 'What browser setting should I use?':")
    for m in matches:
        console.print(f"  • [green]{m['text']}[/green] (similarity: {m['similarity']})")

    # 2. Test Skill Library & Built-in Skills
    console.print("\n[bold cyan]2. Skill Library Catalog:[/bold cyan]")
    skills_table = Table(show_header=True, header_style="bold magenta")
    skills_table.add_column("Skill Name", style="cyan")
    skills_table.add_column("Version", style="yellow")
    skills_table.add_column("Steps", style="green")
    skills_table.add_column("Description", style="white")
    for sk in skill_library.list_skills():
        skills_table.add_row(sk.name, sk.version, str(len(sk.steps)), sk.description)
    console.print(skills_table)

    # 3. Test Skill Executor
    console.print("\n[bold cyan]3. Skill Execution (web_research_and_snapshot):[/bold cyan]")
    exec_res = skill_executor.execute("web_research_and_snapshot", {"url": "https://example.com"})
    console.print(f"Execution Success: [green]{exec_res.get('success')}[/green] in {exec_res.get('duration_s')}s")
    for step in exec_res.get("steps", []):
        console.print(f"  Step {step['step_index']}: {step['name']} -> {'✓' if step['success'] else '✗'}")

    # 4. Test Search -> Learn -> Remember Pipeline
    console.print("\n[bold cyan]4. Search -> Learn -> Remember Pipeline (Skill Acquisition):[/bold cyan]")
    learn_res = skill_learner.learn_and_remember(
        goal="Take screenshot of example.com",
        name="quick_web_screenshot",
        description="Navigate to website and capture page screenshot",
        steps=[
            {"name": "navigate", "action_type": "tool", "target": "browser_goto", "params": {"url": "{{url}}"}},
            {"name": "capture", "action_type": "tool", "target": "browser_screenshot", "params": {}},
        ],
        test_params={"url": "https://example.com"},
    )
    console.print(f"Learned Skill Result: [green]{learn_res.get('message')}[/green]")

    # 5. Inspect Self-Model
    console.print("\n[bold cyan]5. Self-Model Capabilities & Confidence:[/bold cyan]")
    self_table = Table(show_header=True, header_style="bold blue")
    self_table.add_column("Capability", style="cyan")
    self_table.add_column("Category", style="yellow")
    self_table.add_column("Runs", style="white")
    self_table.add_column("Success Rate", style="green")
    self_table.add_column("Confidence", style="magenta")
    for cap in self_model.list_all():
        self_table.add_row(
            cap.capability_name,
            cap.category,
            str(cap.total_runs),
            f"{cap.success_rate}%",
            f"{cap.confidence:.2f}",
        )
    console.print(self_table)

    # 6. Test Manager Memory & Skill Intents
    console.print("\n[bold cyan]6. Manager Routing with Memory & Skills:[/bold cyan]")
    manager = Manager()
    res_mgr = manager.receive("list skills")
    console.print(f"Manager Response:\n{res_mgr}")


if __name__ == "__main__":
    run_phase3_demo()
