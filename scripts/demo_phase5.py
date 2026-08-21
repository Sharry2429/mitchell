"""Demo script testing Phase 5: Reliability, Resource Locking, Recovery, and 'Watch Me' Teaching."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mitchell.core.lock import lock_manager
from mitchell.core.recovery import recovery_engine
from mitchell.core.watchdog import watchdog
from mitchell.skills import skill_executor, skill_library
from mitchell.teaching import teaching_watcher

console = Console()


def run_phase5_demo() -> None:
    console.print(Panel("[bold green]Mitchell Phase 5: Reliability, Teaching & Polish Demo[/bold green]", border_style="cyan"))

    # 1. Global Resource Locking
    console.print("\n[bold cyan]1. Global Resource Lock Manager:[/bold cyan]")
    acq1 = lock_manager.acquire("android_device_usb_1", owner_agent="android_worker", lease_seconds=15.0)
    console.print(f"Agent 'android_worker' acquired 'android_device_usb_1': [green]{acq1}[/green]")
    acq2 = lock_manager.acquire("android_device_usb_1", owner_agent="windows_worker", timeout=0.1)
    console.print(f"Agent 'windows_worker' concurrent collision prevented: [yellow]{not acq2}[/yellow]")
    lock_manager.release("android_device_usb_1", owner_agent="android_worker")
    console.print("Lock released cleanly.")

    # 2. System Watchdog Health Check
    console.print("\n[bold cyan]2. System Watchdog & Heartbeat Inspection:[/bold cyan]")
    health = watchdog.run_health_check()
    health_table = Table(show_header=True, header_style="bold green")
    health_table.add_column("Indicator", style="cyan")
    health_table.add_column("Value", style="white")
    health_table.add_row("Status", f"[bold green]{health['status'].upper()}[/bold green]")
    health_table.add_row("Database Connected", str(health["database_connected"]))
    health_table.add_row("Active Hive Agents", f"{health['registered_agents_count']} agents ({', '.join(health['agents'])})")
    health_table.add_row("Active Locks", str(len(health["active_locks"])))
    console.print(health_table)

    # 3. Checkpoint & Crash Recovery Engine
    console.print("\n[bold cyan]3. State Checkpoint & Recovery Engine:[/bold cyan]")
    chk = recovery_engine.create_checkpoint({"active_goal": "Phase 5 verification", "status": "running"})
    console.print(f"Created Snapshot Checkpoint: [green]{chk.checkpoint_id}[/green]")
    audit = recovery_engine.audit_and_recover()
    console.print(f"Recovery Audit Result: [cyan]{audit['status']}[/cyan] (Latest Checkpoint: {audit['latest_checkpoint']})")

    # 4. Interactive "Watch Me" Teaching Mode
    console.print("\n[bold cyan]4. Interactive 'Watch Me' Teaching Mode:[/bold cyan]")
    teach_res = teaching_watcher.start_session("taught_demo_workflow", description="Taught workflow demonstrating browser and desktop")
    console.print(f"Teaching Session: [cyan]{teach_res['message']}[/cyan]")
    teaching_watcher.record_step("tool", "browser_goto", {"url": "https://news.ycombinator.com"})
    teaching_watcher.record_step("tool", "windows_launch_app", {"cmd": "notepad.exe"})
    fin = teaching_watcher.finalize_skill()
    console.print(f"Finalized Skill: [bold green]{fin['message']}[/bold green]")

    # 5. Execute the freshly taught skill
    console.print("\n[bold cyan]5. Executing Newly Taught Skill:[/bold cyan]")
    exec_res = skill_executor.execute("taught_demo_workflow", {"url": "https://news.ycombinator.com"})
    console.print(f"Execution Result: Success=[green]{exec_res.get('success')}[/green] in {exec_res.get('duration_s')}s")


if __name__ == "__main__":
    run_phase5_demo()
