"""CLI entry points for Mitchell wired to Manager, Pillars, Orb Bridge, Teaching, and Recovery."""

import asyncio
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mitchell.manager import Manager

app = typer.Typer(
    name="mitchell",
    help="Mitchell - Autonomous Multi-Agent Hive & Task Orchestration Framework",
    no_args_is_help=False,
)
console = Console()
manager = Manager()


def show_version() -> None:
    """Display Mitchell version."""
    from mitchell import __version__

    console.print(f"[bold cyan]Mitchell[/bold cyan] version [green]{__version__}[/green]")


def execute_goal(goal: str) -> None:
    """Execute a one-shot goal through the Manager."""
    response = manager.receive(goal)
    console.print(f"[bold cyan][Mitchell][/bold cyan] {response}")


def interactive() -> None:
    """Start the interactive REPL loop connected to the Manager."""
    from mitchell import __version__

    welcome_panel = Panel(
        f"[bold cyan]Mitchell[/bold cyan] [green]v{__version__}[/green]\n"
        "[dim]Autonomous Multi-Agent Hive & Task Orchestration Framework[/dim]\n\n"
        "Type your task or command to begin.\n"
        "Commands:\n"
        "  • [bold yellow]help[/bold yellow] / [bold yellow]tools[/bold yellow] / [bold yellow]skills[/bold yellow] / [bold yellow]agents[/bold yellow] / [bold yellow]self model[/bold yellow] / [bold yellow]cost[/bold yellow]\n"
        "  • [bold yellow]agent browser_worker goto <url>[/bold yellow]\n"
        "  • [bold yellow]agent windows_worker launch <app>[/bold yellow]\n"
        "  • [bold yellow]agent android_worker list_devices[/bold yellow]\n"
        "  • [bold yellow]exit[/bold yellow] / [bold yellow]quit[/bold yellow] to leave.",
        title="[bold green]Welcome to Mitchell[/bold green]",
        border_style="bright_blue",
        padding=(1, 2),
    )
    console.print(welcome_panel)

    while True:
        try:
            user_input = console.input("[bold cyan]mitchell>[/bold cyan] ").strip()
            if not user_input:
                continue

            response = manager.receive(user_input)
            if response.startswith("[exit]"):
                console.print("[dim]Goodbye![/dim]")
                break

            console.print(f"[bold cyan][Mitchell][/bold cyan] {response}")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session interrupted. Goodbye![/dim]")
            break


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show Mitchell version and exit.",
        is_eager=True,
    ),
) -> None:
    """Mitchell CLI entry point."""
    if version:
        show_version()
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        interactive()


@app.command(name="interactive", help="Start interactive REPL mode (default).")
def interactive_command() -> None:
    """Launch interactive REPL mode."""
    interactive()


@app.command(name="version", help="Display Mitchell version.")
def version_command() -> None:
    """Display Mitchell version."""
    show_version()


@app.command(name="do", help="Execute a one-shot goal.")
def do_command(
    goal: str = typer.Argument(..., help="The goal or task description to execute"),
) -> None:
    """Execute a one-shot goal command."""
    execute_goal(goal)


@app.command(name="orb", help="Start the Electron Orb WebSocket bridge server.")
def orb_command(
    host: str = typer.Option("127.0.0.1", help="Host address for WebSocket server"),
    port: int = typer.Option(8765, help="Port for WebSocket server"),
) -> None:
    """Start the Orb WebSocket bridge server."""
    from mitchell.orb.bridge import OrbBridgeServer

    console.print(f"[bold green]Starting Mitchell Orb Bridge on ws://{host}:{port}...[/bold green]")
    server = OrbBridgeServer(host=host, port=port, manager=manager)

    async def _run() -> None:
        await server.start()
        console.print("[bold cyan]Orb Bridge running.[/bold cyan] Launch Electron via: [yellow]cd electron-orb && npm start[/yellow]")
        while True:
            await asyncio.sleep(1)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[dim]Orb Bridge stopped.[/dim]")


@app.command(name="browser", help="Run a quick browser navigation or snapshot task.")
def browser_command(
    action: str = typer.Argument(..., help="Action: goto, snapshot, screenshot, click"),
    target: Optional[str] = typer.Argument(None, help="Target URL or selector"),
) -> None:
    """Direct browser execution command."""
    cmd = f"agent browser_worker {action} {target or ''}".strip()
    response = manager.receive(cmd)
    console.print(f"[bold cyan][Browser Worker][/bold cyan] {response}")


@app.command(name="teach", help="Start interactive 'Watch Me' teaching session.")
def teach_command(
    skill_name: str = typer.Argument(..., help="Name of the skill to teach"),
    description: str = typer.Option("", help="Description of the skill"),
) -> None:
    """Interactive teaching mode."""
    from mitchell.teaching.watcher import teaching_watcher

    console.print(f"[bold green]Starting 'Watch Me' teaching mode for skill '{skill_name}'...[/bold green]")
    res = teaching_watcher.start_session(skill_name, description=description)
    console.print(f"[cyan]{res['message']}[/cyan]")
    console.print("[dim]Enter tool calls or actions sequentially. Type 'done' to finalize or 'cancel' to abort.[/dim]")

    while True:
        try:
            line = console.input("[bold yellow]teach>[/bold yellow] ").strip()
            if not line:
                continue
            if line.lower() == "cancel":
                teaching_watcher.is_active = False
                console.print("[dim]Teaching session cancelled.[/dim]")
                break
            if line.lower() == "done":
                fin = teaching_watcher.finalize_skill()
                console.print(f"[bold green]{fin['message']}[/bold green]")
                break

            # Record step as tool or agent command
            parts = line.split(maxsplit=1)
            target = parts[0]
            params = {"raw": parts[1]} if len(parts) > 1 else {}
            step_res = teaching_watcher.record_step(action_type="tool", target=target, params=params)
            console.print(f"  [dim]Recorded step {step_res.get('step_index')}: {target}[/dim]")
        except (KeyboardInterrupt, EOFError):
            teaching_watcher.is_active = False
            console.print("\n[dim]Teaching session cancelled.[/dim]")
            break


@app.command(name="recover", help="Inspect Event Log and recover interrupted tasks.")
def recover_command() -> None:
    """Crash recovery and state replay audit."""
    from mitchell.core.recovery import recovery_engine

    console.print("[bold cyan]Running Mitchell Recovery & State Audit...[/bold cyan]")
    report = recovery_engine.audit_and_recover()
    console.print(f"Status: [bold green]{report['status']}[/bold green]")
    console.print(f"Recent Events Scanned: {report['total_recent_events_scanned']}")
    console.print(f"Latest Checkpoint: {report['latest_checkpoint']}")
    if report.get("uncompleted_tasks"):
        console.print(f"[yellow]Uncompleted tasks from previous session: {report['uncompleted_tasks']}[/yellow]")
    else:
        console.print("[green]No interrupted tasks found. System clean![/green]")


@app.command(name="health", help="Run comprehensive health check across all pillars.")
def health_command() -> None:
    """Run health check."""
    from mitchell.core.watchdog import watchdog

    report = watchdog.run_health_check()
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Component", style="cyan")
    table.add_column("Status / Details", style="white")
    table.add_row("Overall Health", f"[bold green]{report['status'].upper()}[/bold green]")
    table.add_row("Database Connected", "✓ Yes" if report["database_connected"] else "✗ No")
    table.add_row("Registered Hive Agents", ", ".join(report["agents"]))
    table.add_row("Active Resource Locks", str(len(report["active_locks"])))
    console.print(table)


@app.command(name="cost", help="Display token usage and costs in INR (₹).")
def cost_command() -> None:
    """Display cost summary."""
    from mitchell.core.cost import cost_tracker

    summary = cost_tracker.get_summary()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    for k, v in summary.items():
        table.add_row(k, str(v))
    console.print(table)


def do(goal: Optional[str] = None) -> None:
    """Direct entry point for mitchell-do console script."""
    if goal is None:
        if len(sys.argv) > 1:
            goal = " ".join(sys.argv[1:])
        else:
            console.print("[bold yellow]Usage:[/bold yellow] mitchell-do <goal>")
            raise typer.Exit(code=1)
    execute_goal(goal)


if __name__ == "__main__":
    app()
