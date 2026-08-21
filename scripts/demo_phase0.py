"""Demo script demonstrating Phase 0 foundation: Hive Skeleton, Event Log, and Logging."""

from rich.console import Console
from rich.panel import Panel

from mitchell.core import event_log, logger
from mitchell.hive import hive_router
from mitchell.manager import Manager

console = Console()


def run_demo() -> None:
    console.print(Panel("[bold green]Mitchell Phase 0 Foundation Demo[/bold green]", border_style="cyan"))

    manager = Manager()

    # 1. Test Hive Router direct messaging
    console.print("\n[bold cyan]1. Hive Router Communication:[/bold cyan]")
    logger.info("Directly dispatching message to EchoAgent via HiveRouter")
    hive_res = hive_router.send_message("echo_agent", "Hello Hive Agent!", sender="demo_runner")
    console.print(f"Response: [green]{hive_res}[/green]")
    console.print(f"Agent Inbox: {hive_router.read_inbox('echo_agent')}")
    console.print(f"Agent Outbox: {hive_router.read_outbox('echo_agent')}")

    # 2. Test Manager receiving messages (Fast Intent -> Hive)
    console.print("\n[bold cyan]2. Manager Routing to Hive:[/bold cyan]")
    mgr_res = manager.receive("agent echo_agent Task payload from user")
    console.print(f"Manager Response: [green]{mgr_res}[/green]")

    # 3. Test Manager tool calling
    console.print("\n[bold cyan]3. Manager Tool Invocation:[/bold cyan]")
    tool_res = manager.receive("call tool echo message='Testing tool integration'")
    console.print(f"Manager Tool Response: [green]{tool_res}[/green]")

    # 4. Inspect Event Log
    console.print("\n[bold cyan]4. Event Log Entries:[/bold cyan]")
    recent_events = event_log.get_recent(5)
    for ev in recent_events:
        console.print(f"  • [yellow]{ev.timestamp.strftime('%H:%M:%S')}[/yellow] | [cyan]{ev.type}[/cyan] (from {ev.source}): {ev.data}")


if __name__ == "__main__":
    run_demo()
