"""Device registry for managing USB and Wireless Android devices."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.logging import logger


class AndroidDevice(BaseModel):
    """Registered Android device state and network metadata."""

    serial: str = Field(..., description="Hardware serial or IP:port identifier")
    usb_serial: Optional[str] = Field(default=None, description="Original USB hardware serial")
    ip_address: Optional[str] = Field(default=None, description="Wi-Fi IP address")
    port: int = Field(default=5555, description="ADB TCP/IP port")
    friendly_name: str = Field(default="Android Device", description="Human-readable device label")
    model: Optional[str] = Field(default=None, description="Device brand / model")
    status: str = Field(default="offline", description="online | offline | unauthorized")
    is_wireless: bool = Field(default=False, description="Whether connection is over TCP/IP")
    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last verified active timestamp",
    )


class DeviceRegistry:
    """Persistent store of paired and discovered Android devices."""

    def __init__(self, storage_file: Optional[Path] = None) -> None:
        self.storage_file = Path(storage_file or (Path(settings.data_dir) / "devices.json"))
        self._devices: Dict[str, AndroidDevice] = {}
        self._active_device_id: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load known devices from disk."""
        if self.storage_file.exists():
            try:
                with self.storage_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("devices", []):
                        dev = AndroidDevice.model_validate(item)
                        self._devices[dev.serial] = dev
                    self._active_device_id = data.get("active_device")
            except Exception as e:
                logger.warning("Error loading devices.json: {}", e)

    def _save(self) -> None:
        """Persist device state to disk."""
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_file.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "active_device": self._active_device_id,
                        "devices": [dev.model_dump(mode="json") for dev in self._devices.values()],
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error("Error saving devices.json: {}", e)

    def register(self, device: AndroidDevice) -> AndroidDevice:
        """Register or update an Android device."""
        self._devices[device.serial] = device
        if not self._active_device_id or len(self._devices) == 1:
            self._active_device_id = device.serial
        self._save()
        logger.info("Registered device '{}' ({})", device.friendly_name, device.serial)
        return device

    def get(self, serial_or_id: Optional[str] = None) -> Optional[AndroidDevice]:
        """Get device by serial/IP or retrieve active default device."""
        target_id = serial_or_id or self._active_device_id
        if target_id and target_id in self._devices:
            return self._devices[target_id]
        # Return first online device if active not found
        for dev in self._devices.values():
            if dev.status == "online":
                return dev
        return next(iter(self._devices.values()), None)

    def list_all(self) -> List[AndroidDevice]:
        """Return all registered devices."""
        return list(self._devices.values())

    def set_active(self, serial: str) -> bool:
        """Set the default active device for automation tasks."""
        if serial in self._devices:
            self._active_device_id = serial
            self._save()
            return True
        return False

    def update_status(self, serial: str, status: str) -> None:
        """Update device online/offline status."""
        if serial in self._devices:
            self._devices[serial].status = status
            self._devices[serial].last_seen = datetime.now(timezone.utc)
            self._save()


device_registry = DeviceRegistry()

__all__ = ["AndroidDevice", "DeviceRegistry", "device_registry"]
