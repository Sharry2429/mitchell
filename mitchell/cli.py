"""CLI entry points for Mitchell wired to Manager, Browser Pillar, and Orb Bridge."""

import asyncio
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

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
        "  • [bold yellow]help[/bold yellow] / [bold yellow]list tools[/bold yellow] / [bold yellow]list agents[/bold yellow] / [bold yellow]list events[/bold yellow]\n"
        "  • [bold yellow]agent browser_worker goto <url>[/bold yellow]\n"
        "  • [bold yellow]call tool browser_goto url=<url>[/bold yellow]\n"
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
