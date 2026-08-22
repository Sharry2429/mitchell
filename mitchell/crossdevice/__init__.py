"""Mitchell Peak Cross-Device Control Subsystem — Windows + Android as One Continuous Machine."""

from mitchell.crossdevice.clipboard import ClipboardPayload, CrossDeviceClipboard, cross_device_clipboard
from mitchell.crossdevice.continuity import ContinuityEngine, ContinuityHandoff, continuity_engine
from mitchell.crossdevice.pairing import DevicePairingManager, PairedDevice, device_pairing_manager
from mitchell.crossdevice.phone_link import PhoneLinkBridge, PhoneNotification, phone_link_bridge
from mitchell.crossdevice.scrcpy import ScreenMirrorEngine, screen_mirror_engine
from mitchell.crossdevice.transfer import FileTransferEngine, TransferJob, file_transfer_engine

__all__ = [
    "PhoneLinkBridge",
    "phone_link_bridge",
    "PhoneNotification",
    "CrossDeviceClipboard",
    "cross_device_clipboard",
    "ClipboardPayload",
    "FileTransferEngine",
    "file_transfer_engine",
    "TransferJob",
    "ContinuityEngine",
    "continuity_engine",
    "ContinuityHandoff",
    "DevicePairingManager",
    "device_pairing_manager",
    "PairedDevice",
    "ScreenMirrorEngine",
    "screen_mirror_engine",
]
