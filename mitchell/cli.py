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


@app.command(name="plugin", help="Manage plugins and Claude official marketplace catalog (list, install, uninstall, search).")
def plugin_command(
    action: str = typer.Argument("list", help="Action: list, install, uninstall, search, marketplace"),
    target: Optional[str] = typer.Argument(None, help="Plugin name (e.g. 'github', 'sqlite', 'fetch') or Git URL"),
    marketplace: Optional[str] = typer.Option("claude-plugins-official", help="Source marketplace"),
) -> None:
    """Manage dynamic plugins and Claude Code marketplaces."""
    from mitchell.plugins import plugin_installer, plugin_loader, plugin_marketplace

    act = action.lower()
    if act in ("list", "ls"):
        plugin_loader.discover_and_load_all()
        plugins = plugin_loader.list_plugins()

        table = Table(title="🔌 Mitchell Installed Plugins", border_style="green")
        table.add_column("Name", style="bold green")
        table.add_column("Version", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Author", style="dim")

        for p in plugins:
            table.add_row(p["name"], p["version"], p["description"], p.get("author") or "Community")

        if not plugins:
            console.print("[dim]No plugins installed yet. Try:[/dim] [bold yellow]mitchell plugin install github[/bold yellow]")
        else:
            console.print(table)

    elif act == "install":
        if not target:
            console.print("[bold red]Error:[/bold red] Missing plugin name or URL to install. Example: [yellow]mitchell plugin install github[/yellow]")
            return
        console.print(f"[bold cyan]Installing plugin '{target}' from {marketplace}...[/bold cyan]")
        res = plugin_installer.install(target, marketplace=marketplace)
        if res.get("success"):
            console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
        else:
            console.print(f"[bold red]✗ Failed to install:[/bold red] {res.get('error')}")

    elif act in ("uninstall", "remove", "rm"):
        if not target:
            console.print("[bold red]Error:[/bold red] Missing plugin name to uninstall.")
            return
        res = plugin_installer.uninstall(target)
        if res.get("success"):
            console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
        else:
            console.print(f"[bold red]✗ {res.get('error')}[/bold red]")

    elif act in ("search", "marketplace", "discover"):
        query = target or ""
        results = plugin_marketplace.search_catalog(query)
        table = Table(title="🛒 Claude Official Plugin Marketplace", border_style="cyan")
        table.add_column("Plugin", style="bold cyan")
        table.add_column("Version", style="green")
        table.add_column("Category", style="yellow")
        table.add_column("MCP?", style="magenta")
        table.add_column("Description", style="white")

        for r in results:
            table.add_row(
                r.name,
                r.version,
                r.category,
                "✓ Yes" if r.has_mcp else "No",
                r.description[:75] + ("..." if len(r.description) > 75 else ""),
            )
        console.print(table)
        console.print(f"[dim]Install any plugin via:[/dim] [yellow]mitchell plugin install <name>[/yellow]")


@app.command(name="skill", help="Manage and execute procedural skills and SKILL.md definitions.")
def skill_command(
    action: str = typer.Argument("list", help="Action: list, install, run, info, delete"),
    name_or_file: Optional[str] = typer.Argument(None, help="Skill name or path to SKILL.md"),
    params: Optional[str] = typer.Option(None, "--params", "-p", help="JSON parameters for execution"),
) -> None:
    """Manage and execute procedural skills."""
    from mitchell.skills.executor import skill_executor
    from mitchell.skills.library import skill_library

    act = action.lower()
    if act in ("list", "ls"):
        skills = skill_library.list_skills()
        table = Table(title="🧠 Mitchell Procedural Skill Library", border_style="magenta")
        table.add_column("Skill Name", style="bold magenta")
        table.add_column("Version", style="cyan")
        table.add_column("Source", style="yellow")
        table.add_column("Confidence", style="green")
        table.add_column("Description", style="white")

        for s in skills:
            table.add_row(
                s.name,
                s.version,
                s.source,
                f"{int(s.confidence * 100)}%",
                s.description[:70] + ("..." if len(s.description) > 70 else ""),
            )
        console.print(table)

    elif act == "install":
        if not name_or_file:
            console.print("[bold red]Error:[/bold red] Provide path to a SKILL.md file or skill name.")
            return
        from pathlib import Path
        p = Path(name_or_file)
        if p.exists() and p.is_file():
            skill = skill_library.install_from_file(p)
            console.print(f"[bold green]✓ Installed skill '{skill.name}' (v{skill.version}) from {p.name}[/bold green]")
        else:
            console.print(f"[bold red]File '{name_or_file}' not found.[/bold red]")

    elif act in ("run", "exec"):
        if not name_or_file:
            console.print("[bold red]Error:[/bold red] Missing skill name to execute.")
            return
        import json
        p_dict = {}
        if params:
            try:
                p_dict = json.loads(params)
            except Exception:
                p_dict = {"input": params}

        console.print(f"[bold cyan]Executing skill '{name_or_file}'...[/bold cyan]")
        res = skill_executor.execute(name_or_file, parameters=p_dict)
        if res.get("success"):
            console.print(f"[bold green]✓ Completed in {res.get('duration_s')}s ({len(res.get('steps', []))} steps)[/bold green]")
            for step in res.get("steps", []):
                console.print(f"  • [{step['step_index']}] {step['name']}: [green]{step.get('output', 'OK')}[/green]")
        else:
            console.print(f"[bold red]✗ Execution failed:[/bold red] {res.get('error')}")

    elif act == "info":
        if not name_or_file:
            console.print("[bold red]Error:[/bold red] Missing skill name.")
            return
        skill = skill_library.get_skill(name_or_file)
        if not skill:
            console.print(f"[bold red]Skill '{name_or_file}' not found.[/bold red]")
            return
        from mitchell.skills.parser import SkillMarkdownParser
        md = SkillMarkdownParser.serialize_to_markdown(skill)
        console.print(Panel(md, title=f"Skill: {skill.name}", border_style="cyan"))


@app.command(name="mcp", help="Manage connected external Model Context Protocol (MCP) servers and bridged tools.")
def mcp_command(
    action: str = typer.Argument("list", help="Action: list, add, remove, call"),
    server: Optional[str] = typer.Argument(None, help="MCP Server name"),
    target: Optional[str] = typer.Argument(None, help="Command (for add) or tool name (for call)"),
    args: Optional[str] = typer.Option(None, "--args", "-a", help="Arguments string or JSON"),
) -> None:
    """Manage external Model Context Protocol (MCP) servers."""
    from mitchell.mcp_client.hub import mcp_hub

    act = action.lower()
    if act in ("list", "ls"):
        servers = mcp_hub.list_servers()
        table = Table(title="🌐 External MCP Connected Servers", border_style="cyan")
        table.add_column("Server Name", style="bold cyan")
        table.add_column("Status", style="green")
        table.add_column("Tools", style="yellow")
        table.add_column("Bridged Tool Names", style="white")

        for s in servers:
            table.add_row(
                s["server_name"],
                "Connected" if s["is_connected"] else "Offline",
                str(s["tool_count"]),
                ", ".join(s["tools"][:4]) + ("..." if len(s["tools"]) > 4 else ""),
            )
        if not servers:
            console.print("[dim]No external MCP servers currently active. Add one via:[/dim] [yellow]mitchell mcp add <name> <command>[/yellow]")
        else:
            console.print(table)

    elif act == "add":
        if not server or not target:
            console.print("[bold red]Error:[/bold red] Usage: [yellow]mitchell mcp add <server_name> <command> [--args '...'][/yellow]")
            return
        cmd_args = args.split() if args else []
        console.print(f"[bold cyan]Connecting to stdio MCP server '{server}' ({target})...[/bold cyan]")
        client = mcp_hub.add_stdio_server(server_name=server, command=target, args=cmd_args)
        if client.is_connected:
            console.print(f"[bold green]✓ Connected to '{server}'. Bridged {len(client.remote_tools)} tools into Mitchell ToolRegistry![/bold green]")
        else:
            console.print(f"[bold red]✗ Failed to connect to MCP server '{server}'. Check logs for details.[/bold red]")

    elif act in ("remove", "rm", "delete"):
        if not server:
            console.print("[bold red]Error:[/bold red] Missing server name to remove.")
            return
        if mcp_hub.remove_server(server):
            console.print(f"[bold green]✓ Disconnected and removed MCP server '{server}'[/bold green]")
        else:
            console.print(f"[bold red]Server '{server}' not found.[/bold red]")

    elif act == "call":
        if not server or not target:
            console.print("[bold red]Error:[/bold red] Usage: [yellow]mitchell mcp call <server_name> <tool_name> [--args '...'][/yellow]")
            return
        client = mcp_hub.get_client(server)
        if not client:
            console.print(f"[bold red]MCP server '{server}' not found or not connected.[/bold red]")
            return
        import json
        arg_dict = {}
        if args:
            try:
                arg_dict = json.loads(args)
            except Exception:
                arg_dict = {"input": args}
        console.print(f"[bold cyan]Invoking {server}:{target}...[/bold cyan]")
        res = client.call_tool(target, arguments=arg_dict)
        console.print(Panel(json.dumps(res, indent=2), title=f"MCP Result: {server}:{target}", border_style="green"))


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


@app.command(name="studio", help="Launch Mitchell Studio — the absolute command center.")
def studio_command(
    host: str = typer.Option("127.0.0.1", help="Studio server bind address"),
    port: int = typer.Option(8500, help="Studio server port"),
) -> None:
    """Launch the Studio Command Center web UI."""
    import webbrowser
    from mitchell.studio.server import MitchellStudioServer

    console.print(f"[bold green]🚀 Mitchell Studio Command Center launching on http://{host}:{port}...[/bold green]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    webbrowser.open(f"http://{host}:{port}")
    server = MitchellStudioServer(host=host, port=port)
    server.start()


@app.command(name="avatar", help="Launch interactive 3D Orb Avatar & live audio studio.")
def avatar_command(
    port: int = typer.Option(8550, help="Avatar server port"),
) -> None:
    """Launch 3D Orb Avatar UI."""
    import webbrowser
    from mitchell.studio.server import MitchellStudioServer

    console.print(f"[bold green]🔮 Mitchell 3D Orb Avatar Live on http://127.0.0.1:{port}...[/bold green]")
    server = MitchellStudioServer(host="127.0.0.1", port=port)
    server.start()


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
