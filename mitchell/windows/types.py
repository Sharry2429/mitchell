"""WinControl type definitions — Pydantic models for all return types."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    # Desktop & UI
    "DesktopState",
    "Window",
    "WindowStatus",
    "UIElement",
    "BoundingBox",
    "DisplayInfo",
    "ScreenshotResult",
    "TreeState",
    # Process
    "ProcessInfo",
    # Filesystem
    "FileInfo",
    "DirectoryListing",
    # Registry
    "RegistryValue",
    "RegistryKey",
    # Shell
    "CommandResult",
    # Network
    "NetworkAdapter",
    "NetworkInfo",
    "PingResult",
    "DnsResult",
    "PortInfo",
    # Services
    "ServiceInfo",
    # System
    "SystemInfo",
    "CpuInfo",
    "MemoryInfo",
    "DiskInfo",
    "BatteryInfo",
    # Audio
    "AudioDevice",
    # Power
    "PowerPlan",
]


# ─── Enums ──────────────────────────────────────────────────────────────────


class WindowStatus(str, Enum):
    """Window display state."""

    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    HIDDEN = "hidden"


class ServiceStartType(str, Enum):
    """Windows service startup type."""

    AUTO = "auto"
    MANUAL = "manual"
    DISABLED = "disabled"
    DELAYED_AUTO = "delayed-auto"


class ServiceStatus(str, Enum):
    """Windows service runtime status."""

    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    START_PENDING = "start_pending"
    STOP_PENDING = "stop_pending"
    UNKNOWN = "unknown"


# ─── Desktop & UI ───────────────────────────────────────────────────────────


class BoundingBox(BaseModel):
    """Screen rectangle coordinates."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def get_center(self) -> tuple[int, int]:
        return (self.left + self.right) // 2, (self.top + self.bottom) // 2


class UIElement(BaseModel):
    """Interactive UI element on screen."""

    label: int = 0
    name: str = ""
    control_type: str = ""
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    center: tuple[int, int] = (0, 0)
    window_name: str = ""
    is_enabled: bool = True
    is_focused: bool = False
    value: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Window(BaseModel):
    """Window information."""

    handle: int = 0
    name: str = ""
    class_name: str = ""
    process_id: int = 0
    process_name: str = ""
    status: WindowStatus = WindowStatus.NORMAL
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    is_visible: bool = True


class DisplayInfo(BaseModel):
    """Monitor/display information."""

    index: int = 0
    name: str = ""
    primary: bool = False
    width: int = 0
    height: int = 0
    x: int = 0
    y: int = 0
    dpi_scale: float = 1.0
    bits_per_pixel: int = 32


class TreeState(BaseModel):
    """UI element tree state."""

    interactive_nodes: list[UIElement] = Field(default_factory=list)
    scrollable_nodes: list[UIElement] = Field(default_factory=list)
    root_name: str = "Desktop"


class ScreenshotResult(BaseModel):
    """Screenshot capture result."""

    width: int = 0
    height: int = 0
    scale: float = 1.0
    image_path: str | None = None
    image_bytes: bytes | None = None
    backend: str = "gdi"

    model_config = {"arbitrary_types_allowed": True}


class DesktopState(BaseModel):
    """Complete desktop state snapshot."""

    active_window: Window | None = None
    windows: list[Window] = Field(default_factory=list)
    cursor_position: tuple[int, int] = (0, 0)
    ui_elements: list[UIElement] = Field(default_factory=list)
    scrollable_elements: list[UIElement] = Field(default_factory=list)
    displays: list[DisplayInfo] = Field(default_factory=list)
    screenshot: ScreenshotResult | None = None
    tree_state: TreeState | None = None
    capture_seconds: float = 0.0


# ─── Process ────────────────────────────────────────────────────────────────


class ProcessInfo(BaseModel):
    """Running process information."""

    pid: int = 0
    name: str = ""
    exe: str = ""
    cmdline: list[str] = Field(default_factory=list)
    status: str = ""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    username: str = ""
    create_time: float = 0.0
    parent_pid: int | None = None
    num_threads: int = 0


# ─── Filesystem ─────────────────────────────────────────────────────────────


class FileInfo(BaseModel):
    """File or directory metadata."""

    path: str = ""
    name: str = ""
    is_file: bool = True
    is_dir: bool = False
    size_bytes: int = 0
    size_human: str = ""
    created: str = ""
    modified: str = ""
    accessed: str = ""
    is_hidden: bool = False
    is_readonly: bool = False
    extension: str = ""
    permissions: str = ""


class DirectoryListing(BaseModel):
    """Directory listing result."""

    path: str = ""
    entries: list[FileInfo] = Field(default_factory=list)
    total_files: int = 0
    total_dirs: int = 0
    total_size_bytes: int = 0


# ─── Registry ───────────────────────────────────────────────────────────────


class RegistryValue(BaseModel):
    """Windows registry value."""

    name: str = ""
    data: Any = None
    type: str = ""
    type_id: int = 0


class RegistryKey(BaseModel):
    """Windows registry key with subkeys and values."""

    path: str = ""
    subkeys: list[str] = Field(default_factory=list)
    values: list[RegistryValue] = Field(default_factory=list)


# ─── Shell ──────────────────────────────────────────────────────────────────


class CommandResult(BaseModel):
    """Shell command execution result."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    command: str = ""
    duration_seconds: float = 0.0
    timed_out: bool = False


# ─── Network ────────────────────────────────────────────────────────────────


class NetworkAdapter(BaseModel):
    """Network adapter information."""

    name: str = ""
    description: str = ""
    mac_address: str = ""
    ipv4_address: str = ""
    ipv4_subnet: str = ""
    ipv6_address: str = ""
    gateway: str = ""
    dns_servers: list[str] = Field(default_factory=list)
    status: str = ""
    speed_mbps: int = 0
    adapter_type: str = ""


class NetworkInfo(BaseModel):
    """Complete network information."""

    hostname: str = ""
    adapters: list[NetworkAdapter] = Field(default_factory=list)
    public_ip: str = ""
    is_connected: bool = False


class PingResult(BaseModel):
    """Ping command result."""

    host: str = ""
    resolved_ip: str = ""
    packets_sent: int = 0
    packets_received: int = 0
    packet_loss_percent: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    is_reachable: bool = False


class DnsResult(BaseModel):
    """DNS lookup result."""

    domain: str = ""
    addresses: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    ttl: int = 0


class PortInfo(BaseModel):
    """Open port information."""

    port: int = 0
    protocol: str = "tcp"
    state: str = ""
    pid: int = 0
    process_name: str = ""
    local_address: str = ""
    remote_address: str = ""


# ─── Services ───────────────────────────────────────────────────────────────


class ServiceInfo(BaseModel):
    """Windows service information."""

    name: str = ""
    display_name: str = ""
    status: ServiceStatus = ServiceStatus.UNKNOWN
    start_type: ServiceStartType = ServiceStartType.MANUAL
    description: str = ""
    pid: int = 0
    binary_path: str = ""
    account: str = ""
    dependencies: list[str] = Field(default_factory=list)


# ─── System Info ────────────────────────────────────────────────────────────


class CpuInfo(BaseModel):
    """CPU information."""

    name: str = ""
    cores_physical: int = 0
    cores_logical: int = 0
    max_frequency_mhz: float = 0.0
    current_frequency_mhz: float = 0.0
    usage_percent: float = 0.0
    per_core_percent: list[float] = Field(default_factory=list)


class MemoryInfo(BaseModel):
    """Memory information."""

    total_gb: float = 0.0
    available_gb: float = 0.0
    used_gb: float = 0.0
    usage_percent: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0
    swap_percent: float = 0.0


class DiskInfo(BaseModel):
    """Disk/drive information."""

    device: str = ""
    mountpoint: str = ""
    filesystem: str = ""
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0


class BatteryInfo(BaseModel):
    """Battery status information."""

    percent: float = 0.0
    is_charging: bool = False
    is_plugged: bool = False
    seconds_remaining: int | None = None
    has_battery: bool = False


class SystemInfo(BaseModel):
    """Complete system information."""

    os_name: str = ""
    os_version: str = ""
    os_build: str = ""
    os_architecture: str = ""
    hostname: str = ""
    username: str = ""
    cpu: CpuInfo = Field(default_factory=CpuInfo)
    memory: MemoryInfo = Field(default_factory=MemoryInfo)
    disks: list[DiskInfo] = Field(default_factory=list)
    battery: BatteryInfo = Field(default_factory=BatteryInfo)
    uptime_seconds: float = 0.0
    uptime_human: str = ""
    python_version: str = ""


# ─── Audio ──────────────────────────────────────────────────────────────────


class AudioDevice(BaseModel):
    """Audio device information."""

    name: str = ""
    device_id: str = ""
    is_default: bool = False
    is_enabled: bool = True
    device_type: Literal["playback", "recording"] = "playback"
    volume_percent: float = 0.0
    is_muted: bool = False


# ─── Power ──────────────────────────────────────────────────────────────────


class PowerPlan(BaseModel):
    """Power plan information."""

    name: str = ""
    guid: str = ""
    is_active: bool = False
    description: str = ""
