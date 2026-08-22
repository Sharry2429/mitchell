"""Zero-friction local network pairing and device registry for Windows, Android, and Mesh nodes."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class PairedDevice(BaseModel):
    """Metadata for a registered cross-device endpoint."""

    device_id: str
    name: str
    device_type: str  # 'android_phone' | 'windows_pc' | 'mesh_node' | 'tv_screen'
    ip_address: str = "127.0.0.1"
    port: int = 8600
    is_online: bool = True
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capabilities: List[str] = Field(default_factory=list)


class DevicePairingManager:
    """Discovers, pairs, and manages trusted cross-device endpoints."""

    def __init__(self) -> None:
        self._devices_file = Path(settings.data_dir) / "paired_devices.json"
        self._devices: Dict[str, PairedDevice] = {}
        self._load_devices()

    def _load_devices(self) -> None:
        """Load paired devices from disk."""
        if self._devices_file.exists():
            try:
                data = json.loads(self._devices_file.read_text(encoding="utf-8"))
                for d_id, d_dict in data.items():
                    self._devices[d_id] = PairedDevice.model_validate(d_dict)
            except Exception as e:
                logger.warning("Failed to load paired devices: {}", e)

        # Ensure local device is always registered
        if "local_host" not in self._devices:
            self._devices["local_host"] = PairedDevice(
                device_id="local_host",
                name="Windows Workstation",
                device_type="windows_pc",
                capabilities=["browser", "windows_uia", "storage", "llm", "ide"],
            )

    def _save_devices(self) -> None:
        """Persist paired devices to disk."""
        try:
            self._devices_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.model_dump(mode="json") for k, v in self._devices.items()}
            self._devices_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save paired devices: {}", e)

    def pair_device(
        self,
        device_id: str,
        name: str,
        device_type: str = "android_phone",
        ip_address: str = "127.0.0.1",
        port: int = 8600,
        capabilities: Optional[List[str]] = None,
    ) -> PairedDevice:
        """Register or update a paired device."""
        device = PairedDevice(
            device_id=device_id,
            name=name,
            device_type=device_type,
            ip_address=ip_address,
            port=port,
            capabilities=capabilities or ["adb", "touch", "camera", "media"],
        )
        self._devices[device_id] = device
        self._save_devices()

        event_log.log_event(
            "device_paired",
            source="pairing_manager",
            data={"id": device_id, "name": name, "type": device_type},
        )
        logger.info("Device '{}' ({}) paired successfully at {}:{}", name, device_type, ip_address, port)
        return device

    def list_devices(self) -> List[Dict[str, Any]]:
        """List all paired devices."""
        # Also probe ADB for connected Android phones
        try:
            from mitchell.android.engine import android_engine
            if android_engine.is_connected():
                if "android_adb" not in self._devices:
                    self.pair_device(
                        device_id="android_adb",
                        name="Connected Android Device",
                        device_type="android_phone",
                        capabilities=["adb", "touch", "sms", "calls", "apps"],
                    )
        except Exception:
            pass

        return [d.model_dump(mode="json") for d in self._devices.values()]


device_pairing_manager = DevicePairingManager()

__all__ = ["PairedDevice", "DevicePairingManager", "device_pairing_manager"]
