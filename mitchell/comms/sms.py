"""SMS and phone call management via Phone Link and wireless ADB."""

from typing import Any, Dict, Optional

from mitchell.comms.hub import communication_hub
from mitchell.crossdevice.phone_link import phone_link_bridge


class SMSManager:
    """Dispatches and aggregates SMS messages across connected mobile devices."""

    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Phone Link or ADB."""
        res = phone_link_bridge.send_sms(phone_number=phone_number, message=message)

        # Record in unified hub
        communication_hub.record_message(
            channel="sms",
            sender="me",
            recipient=phone_number,
            content=message,
            is_incoming=False,
            metadata=res,
        )
        return res


class CallManager:
    """Manages outgoing and mirrored phone calls."""

    def make_call(self, phone_number: str) -> Dict[str, Any]:
        """Initiate call via mobile device."""
        return phone_link_bridge.initiate_call(phone_number)


sms_manager = SMSManager()
call_manager = CallManager()

__all__ = ["SMSManager", "sms_manager", "CallManager", "call_manager"]
