"""
WinControl — Universal Windows Control Library
================================================

Complete programmatic control over Windows at every level:
- **Low-level**: Win32 API, ctypes, COM/UIA automation
- **UI-level**: Screen capture, UI element inspection, input simulation
- **High-level**: App management, process control, file operations
- **Shell-level**: Admin PowerShell, CMD, script execution
- **System-level**: Registry, services, network, audio, power management

Quick Start::

    import mitchell.windows as wc

    # Configure (optional — safeguards are ON by default)
    wc.configure(safeguards=False)  # Unrestricted mode

    # Desktop & Vision
    state = wc.snapshot()
    wc.screenshot(save_path="screen.png")

    # Input
    wc.click(500, 300)
    wc.type_text("Hello World")
    wc.hotkey("ctrl", "s")

    # Shell (admin-level)
    result = wc.powershell("Get-Process")
    result = wc.powershell_admin("Set-ExecutionPolicy RemoteSigned")

    # Apps & Processes
    wc.open_app("Notepad")
    wc.focus_window("Notepad")
    procs = wc.list_processes()

    # System
    info = wc.get_system_info()
    wc.lock_screen()

    # LLM Integration
    from mitchell.windows.schema import get_tools_schema
    from mitchell.windows.executor import execute_tool
    tools = get_tools_schema(format="openai")
    result = execute_tool("screenshot", {})
"""

from __future__ import annotations

__version__ = "0.1.0"

# ─── Configuration ──────────────────────────────────────────────────────────
# ─── Apps (App, Filesystem, Scrape) ───────────────────────────────────────
from mitchell.windows.apps import (
    close_window,
    copy,
    delete,
    download_file,
    exists,
    file_info,
    focus_window,
    get_page_links,
    get_page_title,
    get_size,
    is_app_running,
    launch_executable,
    list_dir,
    list_installed_apps,
    make_dir,
    maximize_window,
    minimize_window,
    move,
    move_window,
    open_app,
    read_file,
    resize_window,
    restore_window,
    scrape_text,
    scrape_url,
    search_files,
    write_file,
)
from mitchell.windows.config import WinControlConfig, configure, get_config

# ─── Hardware (Audio, Display, Network) ───────────────────────────────────
from mitchell.windows.hardware import (
    add_firewall_rule,
    connect_wifi,
    disconnect_wifi,
    dns_lookup,
    flush_dns,
    get_audio_devices,
    get_brightness,
    get_display_resolution,
    get_dpi_scale,
    get_firewall_status,
    get_ip_addresses,
    get_network_adapters,
    get_network_info,
    get_open_ports,
    get_primary_display,
    get_public_ip,
    get_screen_size,
    get_volume,
    get_wifi_networks,
    is_muted,
    mute,
    ping,
    remove_firewall_rule,
    set_brightness,
    set_default_device,
    set_volume,
    toggle_mute,
    traceroute,
    unmute,
    volume_down,
    volume_up,
)

# ─── STT (Speech-to-Text) ────────────────────────────────────────────────
from mitchell.windows.stt import listen_and_transcribe

# ─── System (Power, Process, Shell, Sysinfo, Registry, Services) ──────────
from mitchell.windows.system import (
    cancel_shutdown,
    cmd,
    get_active_power_plan,
    get_battery_info,
    get_cpu_info,
    get_cpu_usage,
    get_disk_info,
    get_environment_variables,
    get_event_log,
    get_installed_programs,
    get_memory_info,
    get_power_plans,
    get_process,
    get_process_cpu,
    get_process_memory,
    get_service,
    get_service_config,
    get_service_status,
    get_sleep_timeout,
    get_startup_programs,
    get_system_info,
    get_uptime,
    get_uptime_human,
    get_windows_version,
    hibernate,
    is_process_running,
    is_service_running,
    kill_process,
    list_processes,
    list_services,
    lock_screen,
    log_off,
    pipe,
    powershell,
    powershell_admin,
    process_tree,
    reg_create_key,
    reg_delete,
    reg_delete_key,
    reg_key_exists,
    reg_list_keys,
    reg_list_values,
    reg_read,
    reg_write,
    restart,
    restart_service,
    run_background,
    run_script,
    set_environment_variable,
    set_power_plan,
    set_service_startup,
    set_sleep_timeout,
    shutdown,
    sleep,
    start_process,
    start_service,
    stop_service,
    which,
)

# ─── TTS (Text-to-Speech) ────────────────────────────────────────────────
from mitchell.windows.tts import get_voices, speak

# ─── Types (for type annotations in user code) ─────────────────────────────
from mitchell.windows.types import (
    # Audio
    AudioDevice,
    BatteryInfo,
    BoundingBox,
    # Shell
    CommandResult,
    CpuInfo,
    # Desktop & UI
    DesktopState,
    DirectoryListing,
    DiskInfo,
    DisplayInfo,
    DnsResult,
    # Filesystem
    FileInfo,
    MemoryInfo,
    # Network
    NetworkAdapter,
    NetworkInfo,
    PingResult,
    PortInfo,
    # Power
    PowerPlan,
    # Process
    ProcessInfo,
    RegistryKey,
    # Registry
    RegistryValue,
    ScreenshotResult,
    # Services
    ServiceInfo,
    # System
    SystemInfo,
    TreeState,
    UIElement,
    Window,
    WindowStatus,
)

# ─── UI (Desktop, Input, Clipboard, Notification) ─────────────────────────
from mitchell.windows.ui import (
    clear_clipboard,
    click,
    double_click,
    drag,
    find_element,
    get_active_window,
    get_clipboard,
    get_clipboard_formats,
    get_clipboard_image,
    get_cursor_position,
    get_displays,
    get_mouse_position,
    get_ui_elements,
    get_window_by_title,
    get_windows,
    hotkey,
    key_down,
    key_up,
    middle_click,
    move_mouse,
    press_key,
    right_click,
    screenshot,
    scroll,
    send_alert,
    send_notification,
    set_clipboard,
    set_clipboard_image,
    snapshot,
    type_text,
    wait,
    wait_for,
)

# ─── Convenience: All public names ─────────────────────────────────────────
__all__ = [
    # Config
    "configure",
    "get_config",
    "WinControlConfig",
    "__version__",
    # Desktop
    "snapshot",
    "screenshot",
    "get_windows",
    "get_active_window",
    "get_cursor_position",
    "get_displays",
    "get_ui_elements",
    "find_element",
    "get_window_by_title",
    # Input
    "click",
    "double_click",
    "right_click",
    "middle_click",
    "move_mouse",
    "drag",
    "scroll",
    "get_mouse_position",
    "type_text",
    "press_key",
    "hotkey",
    "key_down",
    "key_up",
    "wait",
    "wait_for",
    # App
    "open_app",
    "launch_executable",
    "focus_window",
    "close_window",
    "minimize_window",
    "maximize_window",
    "restore_window",
    "resize_window",
    "move_window",
    "list_installed_apps",
    "is_app_running",
    # Shell
    "powershell",
    "powershell_admin",
    "cmd",
    "run_script",
    "run_background",
    "pipe",
    "which",
    # Filesystem
    "list_dir",
    "read_file",
    "write_file",
    "copy",
    "move",
    "delete",
    "exists",
    "file_info",
    "search_files",
    "make_dir",
    "get_size",
    # Clipboard
    "get_clipboard",
    "set_clipboard",
    "get_clipboard_image",
    "set_clipboard_image",
    "clear_clipboard",
    "get_clipboard_formats",
    # Registry
    "reg_read",
    "reg_write",
    "reg_delete",
    "reg_list_keys",
    "reg_list_values",
    "reg_key_exists",
    "reg_create_key",
    "reg_delete_key",
    # Process
    "list_processes",
    "get_process",
    "kill_process",
    "start_process",
    "process_tree",
    "is_process_running",
    "get_process_cpu",
    "get_process_memory",
    # Notification
    "send_notification",
    "send_alert",
    # Display
    "get_primary_display",
    "get_display_resolution",
    "get_dpi_scale",
    "get_screen_size",
    "set_brightness",
    "get_brightness",
    # Scrape
    "scrape_url",
    "scrape_text",
    "get_page_title",
    "get_page_links",
    "download_file",
    # Network
    "get_network_adapters",
    "get_network_info",
    "get_ip_addresses",
    "get_public_ip",
    "get_wifi_networks",
    "connect_wifi",
    "disconnect_wifi",
    "ping",
    "traceroute",
    "get_open_ports",
    "dns_lookup",
    "get_firewall_status",
    "add_firewall_rule",
    "remove_firewall_rule",
    "flush_dns",
    # Services
    "list_services",
    "get_service",
    "start_service",
    "stop_service",
    "restart_service",
    "get_service_status",
    "set_service_startup",
    "is_service_running",
    "get_service_config",
    # Sysinfo
    "get_system_info",
    "get_cpu_info",
    "get_cpu_usage",
    "get_memory_info",
    "get_disk_info",
    "get_battery_info",
    "get_uptime",
    "get_uptime_human",
    "get_environment_variables",
    "set_environment_variable",
    "get_installed_programs",
    "get_windows_version",
    "get_event_log",
    "get_startup_programs",
    # Audio
    "get_volume",
    "set_volume",
    "mute",
    "unmute",
    "toggle_mute",
    "is_muted",
    "volume_up",
    "volume_down",
    "get_audio_devices",
    "set_default_device",
    # Power
    "shutdown",
    "restart",
    "cancel_shutdown",
    "sleep",
    "hibernate",
    "lock_screen",
    "log_off",
    "get_power_plans",
    "get_active_power_plan",
    "set_power_plan",
    "get_sleep_timeout",
    "set_sleep_timeout",
    # TTS
    "speak",
    "get_voices",
    # STT
    "listen_and_transcribe",
    # Types (re-exported for convenience)
    "DesktopState",
    "Window",
    "WindowStatus",
    "UIElement",
    "BoundingBox",
    "DisplayInfo",
    "ScreenshotResult",
    "TreeState",
    "ProcessInfo",
    "FileInfo",
    "DirectoryListing",
    "RegistryValue",
    "RegistryKey",
    "CommandResult",
    "NetworkAdapter",
    "NetworkInfo",
    "PingResult",
    "DnsResult",
    "PortInfo",
    "ServiceInfo",
    "SystemInfo",
    "CpuInfo",
    "MemoryInfo",
    "DiskInfo",
    "BatteryInfo",
    "AudioDevice",
    "PowerPlan",
]
