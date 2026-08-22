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


@app.command(name="serve", help="Start the Mitchell REST API & Webhook server.")
def serve_command(
    host: str = typer.Option("127.0.0.1", help="Host address for HTTP REST API"),
    port: int = typer.Option(8000, help="Port for HTTP REST API"),
) -> None:
    """Start REST API server."""
    from mitchell.api.server import MitchellAPIServer

    console.print(f"[bold green]Starting Mitchell REST API Server on http://{host}:{port}...[/bold green]")
    server = MitchellAPIServer(host=host, port=port)
    try:
        server.start()
    except KeyboardInterrupt:
        console.print("\n[dim]REST API Server stopped.[/dim]")


@app.command(name="research", help="Run autonomous deep web research on a topic.")
def research_command(
    topic: str = typer.Argument(..., help="Research topic or question to investigate"),
) -> None:
    """Execute deep research command."""
    from mitchell.browser.researcher import deep_researcher

    console.print(f"[bold cyan]Initiating deep web research on:[/bold cyan] [white]'{topic}'[/white]...")
    report = asyncio.run(deep_researcher.research(topic=topic))
    console.print(Panel(f"[bold green]Research Briefing: {report.topic}[/bold green]\n\n{report.summary}", border_style="cyan"))
    console.print(f"[bold cyan]Sources Inspected ({len(report.sources)}):[/bold cyan]")
    for s in report.sources:
        console.print(f"  • {s.url} ({'✓ Verified' if s.success else '✗ Failed'})")


@app.command(name="voice", help="Start interactive voice conversation mode (wake word: 'hey mitchell').")
def voice_command() -> None:
    """Launch voice interaction loop."""
    from mitchell.voice import voice_mode

    console.print("[bold green]Starting Mitchell Voice Mode...[/bold green]")
    console.print("[dim]Say 'hey Mitchell' to wake up. Say 'stop' to go back to sleep. Ctrl+C to exit.[/dim]")
    try:
        voice_mode.run_loop()
    except KeyboardInterrupt:
        console.print("\n[dim]Voice mode stopped.[/dim]")


@app.command(name="launch", help="Launch all Mitchell services (Orb + REST API + Voice).")
def launch_command(
    api_port: int = typer.Option(8000, help="REST API port"),
    orb: bool = typer.Option(True, help="Start WebSocket Orb bridge"),
) -> None:
    """Unified launcher starting all Mitchell services."""
    import threading
    from mitchell.api.server import MitchellAPIServer

    console.print("[bold green]🚀 Mitchell Unified Launcher[/bold green]")
    console.print(f"  • REST API: http://127.0.0.1:{api_port}")

    threads = []

    # REST API thread
    api_server = MitchellAPIServer(host="127.0.0.1", port=api_port)
    t_api = threading.Thread(target=api_server.start, daemon=True, name="api-server")
    t_api.start()
    threads.append(t_api)
    console.print("  [green]✓[/green] REST API Server started")

    # Orb WebSocket bridge
    if orb:
        from mitchell.orb.bridge import orb_bridge
        t_orb = threading.Thread(target=lambda: asyncio.run(orb_bridge.start()), daemon=True, name="orb-bridge")
        t_orb.start()
        threads.append(t_orb)
        console.print("  [green]✓[/green] Orb WebSocket Bridge started")

    console.print("\n[bold cyan]All services running. Press Ctrl+C to stop.[/bold cyan]")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Shutting down services...[/dim]")


@app.command(name="evolve", help="Trigger recursive self-evolution (inspect codebase, synthesize tools, run tests).")
def evolve_command(
    inspect: bool = typer.Option(False, "--inspect", "-i", help="Inspect local codebase and tool architecture"),
    verify: bool = typer.Option(True, "--verify", "-v", help="Run full test suite verification"),
) -> None:
    """Trigger recursive self-evolution."""
    from mitchell.evolution import code_inspector, evolution_engine

    if inspect:
        summary = code_inspector.get_system_summary()
        console.print(Panel(
            f"[bold cyan]Source Files:[/bold cyan] {summary['total_source_files']}\n"
            f"[bold cyan]Test Files:[/bold cyan] {summary['total_test_files']}\n"
            f"[bold cyan]Registered Tools:[/bold cyan] {summary['total_registered_tools']}\n"
            f"[bold cyan]Packages:[/bold cyan] {', '.join(summary['packages'])}",
            title="🧬 Mitchell Codebase Architecture",
            border_style="green",
        ))
        return

    console.print("[bold green]🧬 Running Mitchell Self-Evolution Verification Loop...[/bold green]")
    test_res = evolution_engine.run_test_suite()
    if test_res.get("success"):
        console.print(Panel("[bold green]✓ System Invariants & Test Suite Fully Verified.[/bold green]", border_style="green"))
    else:
        console.print(Panel(f"[bold red]✗ Test Failures Detected:[/bold red]\n{test_res.get('stdout')}", border_style="red"))


@app.command(name="butler", help="Launch 24/7 autonomous background queue worker.")
def butler_command(
    poll_interval: float = typer.Option(1.0, help="Polling interval in seconds"),
) -> None:
    """Start 24/7 background butler."""
    from mitchell.daemon import butler

    console.print("[bold green]🎩 Mitchell 24/7 Autonomous Butler Starting...[/bold green]")
    console.print("[dim]Draining task queue and executing scheduled cron routines. Press Ctrl+C to stop.[/dim]")
    butler.start_loop(poll_interval_s=poll_interval)


@app.command(name="schedule", help="Schedule a recurring autonomous routine.")
def schedule_command(
    cron: str = typer.Argument(..., help="5-field cron expression (e.g. '0 8 * * *')"),
    goal: str = typer.Argument(..., help="Autonomous goal description"),
    name: str = typer.Option("job_custom", help="Unique identifier for schedule"),
) -> None:
    """Schedule recurring cron routine."""
    from mitchell.daemon import cron_scheduler

    job = cron_scheduler.add_job(job_id=name, cron_expr=cron, goal=goal)
    console.print(f"[bold green]✓ Scheduled recurring job:[/bold green] [cyan]{job.job_id}[/cyan] ({cron}) -> '{goal}'")


@app.command(name="mesh", help="Manage distributed multi-node mesh cluster.")
def mesh_command(
    list_nodes: bool = typer.Option(True, "--list", "-l", help="List active mesh nodes"),
) -> None:
    """Manage distributed mesh cluster."""
    from mitchell.mesh import mesh_coordinator

    nodes = mesh_coordinator.list_nodes()
    table = Table(title="🛰️ Mitchell Distributed Mesh Cluster", border_style="cyan")
    table.add_column("Node ID", style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Platform", style="green")
    table.add_column("Capabilities", style="yellow")
    table.add_column("Load", style="magenta")

    for n in nodes:
        table.add_row(
            n["node_id"],
            n["node_name"],
            n["platform"],
            ", ".join(n["capabilities"]),
            f"{n['load_score']:.1f}",
        )
    console.print(table)


@app.command(name="plugin", help="Discover and manage drop-in plugins.")
def plugin_command(
    discover: bool = typer.Option(True, "--discover", "-d", help="Discover and list installed plugins"),
) -> None:
    """Manage dynamic plugins."""
    from mitchell.plugins import plugin_loader

    plugin_loader.discover_and_load_all()
    plugins = plugin_loader.list_plugins()

    table = Table(title="🔌 Mitchell Active Plugins", border_style="green")
    table.add_column("Name", style="bold green")
    table.add_column("Version", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Author", style="dim")

    for p in plugins:
        table.add_row(p["name"], p["version"], p["description"], p.get("author") or "Community")

    if not plugins:
        console.print("[dim]No drop-in plugins found in .mitchell/plugins/ directory.[/dim]")
    else:
        console.print(table)


@app.command(name="studio", help="Launch the real-time Visual Workflow Studio web UI.")
def studio_command(
    port: int = typer.Option(8500, help="Studio HTTP server port"),
) -> None:
    """Launch the visual workflow studio."""
    from mitchell.studio import MitchellStudioServer

    console.print(f"[bold green]🎨 Mitchell Visual Workflow Studio starting on http://127.0.0.1:{port}...[/bold green]")
    server = MitchellStudioServer(host="127.0.0.1", port=port)
    server.start()


@app.command(name="benchmark", help="Execute multi-agent benchmarking evaluation arena.")
def benchmark_command(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain (browser, windows, android, reasoning, vision)"),
) -> None:
    """Run benchmark evaluation suite."""
    from mitchell.benchmark import benchmark_runner, BENCHMARK_SUITE

    scenarios = BENCHMARK_SUITE
    if domain:
        scenarios = [s for s in BENCHMARK_SUITE if s.domain == domain]

    console.print(f"[bold green]🏆 Running Mitchell Benchmark Arena ({len(scenarios)} challenges)...[/bold green]")
    scorecard = benchmark_runner.run_suite(scenarios=scenarios)
    report = scorecard.generate_markdown_report()
    console.print(Panel(report, border_style="cyan", title="Benchmark Results"))


@app.command(name="security", help="Inspect security guardrail permissions and audit hash integrity.")
def security_command(
    audit: bool = typer.Option(True, "--audit", "-a", help="Run cryptographic audit check"),
) -> None:
    """Check security guardrails and audit integrity."""
    from mitchell.security import security_guardrail

    hash_val = security_guardrail.calculate_log_chain_hash()
    console.print(Panel(
        f"[bold green]✓ Security Guardrails Active[/bold green]\n"
        f"[bold cyan]Audit Log SHA256 Chain Hash:[/bold cyan] {hash_val[:16]}...{hash_val[-16:]}\n"
        f"[bold cyan]Action Risk Policy:[/bold cyan] Tiered Read-Only / Confirmation Required",
        title="🛡️ Mitchell Security Policy",
        border_style="green",
    ))


@app.command(name="deploy", help="Generate production deployment configs (systemd / Caddy).")
def deploy_command(
    service: str = typer.Option("butler", help="Service name (butler, studio)"),
    caddy: bool = typer.Option(False, "--caddy", help="Generate Caddy reverse proxy config"),
) -> None:
    """Generate production deploy configurations."""
    from mitchell.deploy import vps_deployer

    if caddy:
        cfg = vps_deployer.generate_caddyfile()
        console.print(Panel(cfg, title="Caddyfile Configuration", border_style="cyan"))
    else:
        unit = vps_deployer.generate_systemd_unit(service_type=service)
        console.print(Panel(unit, title=f"Systemd Service Unit ({service})", border_style="green"))


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
