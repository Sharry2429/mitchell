"""Demo script testing Phase 2: Windows + Android Pillars and Worker Agents."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mitchell.android.registry import device_registry
from mitchell.core import event_log
from mitchell.hive import hive_router
from mitchell.manager import Manager
from mitchell.tools import tool_registry
from mitchell.windows.engine import windows_engine

console = Console()


def run_phase2_demo() -> None:
    console.print(Panel("[bold green]Mitchell Phase 2: Windows + Android Pillars Demo[/bold green]", border_style="cyan"))

    # 1. Inspect All Registered Hive Agents (Echo, Browser, Windows, Android)
    console.print("\n[bold cyan]1. Hive Multi-Pillar Agents:[/bold cyan]")
    agents_table = Table(show_header=True, header_style="bold magenta")
    agents_table.add_column("Agent ID", style="cyan")
    agents_table.add_column("Description", style="white")
    for ag in hive_router.list_agents():
        agents_table.add_row(ag["agent_id"], ag["description"])
    console.print(agents_table)

    # 2. Test Tool Registry Auto-Discovery
    console.print("\n[bold cyan]2. Auto-Discovered Tools Across All Pillars:[/bold cyan]")
    tools = tool_registry.list_tools()
    console.print(f"Total tools discovered: [green]{len(tools)}[/green]")
    for t in tools:
        console.print(f"  • [yellow]{t['name']}[/yellow]: {t['description']}")

    # 3. Test Windows Worker via Manager
    console.print("\n[bold cyan]3. Manager Routing to Windows Worker (List Windows):[/bold cyan]")
    manager = Manager()
    res_win = manager.receive("agent windows_worker list_windows")
    console.print(f"Response:\n[dim]{res_win[:250]}...[/dim]")

    # 4. Test Android Worker via Manager
    console.print("\n[bold cyan]4. Manager Routing to Android Worker (List Devices):[/bold cyan]")
    res_android = manager.receive("agent android_worker list_devices")
    console.print(f"Response: [green]{res_android}[/green]")

    # 5. Inspect Event Log
    console.print("\n[bold cyan]5. Event Log Entries:[/bold cyan]")
    recent_events = event_log.get_recent(5)
    for ev in recent_events:
        console.print(f"  • [yellow]{ev.timestamp.strftime('%H:%M:%S')}[/yellow] | [cyan]{ev.type}[/cyan] (from {ev.source}): {ev.data}")


if __name__ == "__main__":
    run_phase2_demo()
