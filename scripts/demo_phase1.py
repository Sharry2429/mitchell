"""Demo script testing Phase 1: Browser Pillar, Human Mouse, Stealth, Captcha, and Hive Worker."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mitchell.browser.mouse import generate_bezier_curve
from mitchell.core import event_log
from mitchell.hive import hive_router
from mitchell.manager import Manager

console = Console()


def run_phase1_demo() -> None:
    console.print(Panel("[bold green]Mitchell Phase 1: Orb + Browser Pillar Demo[/bold green]", border_style="cyan"))

    # 1. Test Bezier curve human mouse trajectory generation
    console.print("\n[bold cyan]1. Human-Like Mouse Trajectory (Bezier Curve):[/bold cyan]")
    start = (100.0, 100.0)
    end = (640.0, 480.0)
    curve_points = generate_bezier_curve(start, end, num_points=10)
    console.print(f"Generated {len(curve_points)} trajectory points from {start} to {end}:")
    for i, pt in enumerate(curve_points[:5]):
        console.print(f"  Step {i+1}: ({pt[0]:.2f}, {pt[1]:.2f})")
    console.print("  ...")

    # 2. Inspect Registered Hive Agents (including BrowserWorkerAgent)
    console.print("\n[bold cyan]2. Registered Hive Agents:[/bold cyan]")
    agents_table = Table(show_header=True, header_style="bold magenta")
    agents_table.add_column("Agent ID", style="cyan")
    agents_table.add_column("Description", style="white")
    for ag in hive_router.list_agents():
        agents_table.add_row(ag["agent_id"], ag["description"])
    console.print(agents_table)

    # 3. Manager routing to Browser Worker
    console.print("\n[bold cyan]3. Manager Routing to Browser Worker:[/bold cyan]")
    manager = Manager()
    res = manager.receive("agent browser_worker goto https://example.com")
    console.print(f"Manager Response: [green]{res}[/green]")

    # 4. Inspect Event Log
    console.print("\n[bold cyan]4. Event Log Entries:[/bold cyan]")
    recent_events = event_log.get_recent(6)
    for ev in recent_events:
        console.print(f"  • [yellow]{ev.timestamp.strftime('%H:%M:%S')}[/yellow] | [cyan]{ev.type}[/cyan] (from {ev.source}): {ev.data}")


if __name__ == "__main__":
    run_phase1_demo()
