import urllib.parse
from typing import Any

from mitchell.android import adb
from mitchell.android.base import require_enabled
from mitchell.android.notification import get_active_notifications
from mitchell.core.audit import log_action
from mitchell.core.result import MCPResult

"\nmitchell.android.phone\nPhone calling and call history management via ADB.\n"


def place_call(number: str) -> MCPResult:
    """Place a phone call to a specific number. Requires CALL_PHONE permission."""
    try:
        require_enabled("phone", "place_call")
        adb.shell(f"am start -a android.intent.action.CALL -d tel:{number}")
        return MCPResult.success(f"Call initiated to {number}")
    except Exception as e:
        return MCPResult.fail(str(e))


def open_dialer(number: str = "") -> MCPResult:
    """Open the dialer, optionally pre-filled with a number."""
    try:
        adb.shell(f"am start -a android.intent.action.DIAL -d tel:{number}")
        return MCPResult.success(f"Dialer opened for {number}")
    except Exception as e:
        return MCPResult.fail(str(e))





def get_call_history(limit: int = 50) -> MCPResult:
    """Get recent call history. Requires READ_CALL_LOG permission."""
    try:
        output = adb.shell(
            "content query --uri content://call_log/calls --projection number:type:duration:date"
        )
        if "Permission Denial" in output:
            return MCPResult.fail("Requires READ_CALL_LOG permission.")
        history = []
        for line in output.splitlines():
            if not line.strip() or "No result found" in line:
                continue
            parts = line.split(", ")
            entry: dict[str, Any] = {}
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    k = k.strip()
                    if k.startswith("Row:"):
                        k = k.split(" ", 2)[-1].strip()
                    if k == "type":
                        v_int = int(v)
                        entry["type"] = (
                            "INCOMING"
                            if v_int == 1
                            else (
                                "OUTGOING"
                                if v_int == 2
                                else "MISSED" if v_int == 3 else str(v_int)
                            )
                        )
                    else:
                        entry[k] = v
            history.append(entry)
            if len(history) >= limit:
                break
        return MCPResult.success(history)
    except Exception as e:
        return MCPResult.fail(str(e))


"\nAndroid SMS management via ADB content provider queries.\n"


def read(limit: int = 10, offset: int = 0) -> MCPResult:
    """Reads recent SMS messages via content provider query."""
    log_action("sms", "read", {"limit": limit, "offset": offset}, {})
    try:
        result = adb.shell(
            [
                "content",
                "query",
                "--uri",
                "content://sms/inbox",
                "--projection",
                "address:body:date",
                "--sort",
                f"date DESC LIMIT {limit} OFFSET {offset}",
            ]
        )
        messages = []
        if result:
            for line in result.strip().splitlines():
                if "Row:" in line:
                    parts = {}
                    for pair in line.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            parts[k.strip()] = v.strip()
                    messages.append(parts)
        return MCPResult.success(messages)
    except Exception as e:
        return MCPResult.fail(str(e))


def send(phone_number: str, message: str) -> MCPResult:
    """Sends an SMS via ADB am start (opens the SMS app with pre-filled content)."""
    log_action("sms", "send", {"phone": phone_number, "msg_len": len(message)}, {})
    try:
        adb.shell(
            [
                "am",
                "start",
                "-a",
                "android.intent.action.SENDTO",
                "-d",
                f"sms:{phone_number}",
                "--es",
                "sms_body",
                message,
                "--ez",
                "exit_on_sent",
                "true",
            ]
        )
        return MCPResult.success(None)
    except Exception as e:
        return MCPResult.fail(str(e))


"\nAndroid contacts management via ADB content provider queries.\n"


def list_contacts() -> MCPResult:
    """Lists all contacts via content provider query."""
    log_action("contacts", "list_contacts", {}, {})
    try:
        result = adb.shell(
            [
                "content",
                "query",
                "--uri",
                "content://contacts/phones/",
                "--projection",
                "_id:display_name:number",
            ]
        )
        contacts = []
        if result:
            for line in result.strip().splitlines():
                if "Row:" in line:
                    parts = {}
                    for pair in line.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            parts[k.strip()] = v.strip()
                    contacts.append(parts)
        return MCPResult.success(contacts)
    except Exception as e:
        return MCPResult.fail(str(e))


def get_contact(contact_id: str) -> MCPResult:
    """Retrieves a specific contact by ID."""
    log_action("contacts", "get_contact", {"id": contact_id}, {})
    try:
        result = adb.shell(
            [
                "content",
                "query",
                "--uri",
                f"content://contacts/phones/{contact_id}",
                "--projection",
                "_id:display_name:number",
            ]
        )
        if result:
            for line in result.strip().splitlines():
                if "Row:" in line:
                    parts = {}
                    for pair in line.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            parts[k.strip()] = v.strip()
                    return MCPResult.success(parts)
        return MCPResult.success(None)
    except Exception as e:
        return MCPResult.fail(str(e))


def add_contact(name: str, phone: str) -> MCPResult:
    """Opens the contacts app with pre-filled data to add a new contact."""
    log_action("contacts", "add_contact", {"name": name}, {})
    try:
        result = adb.shell(
            [
                "am",
                "start",
                "-a",
                "android.intent.action.INSERT",
                "-t",
                "vnd.android.cursor.dir/contact",
                "--es",
                "name",
                name,
                "--es",
                "phone",
                phone,
            ]
        )
        return MCPResult.success(result.strip() if result else "")
    except Exception as e:
        return MCPResult.fail(str(e))


def delete_contact(contact_id: str) -> MCPResult:
    """Deletes a contact by ID. Requires appropriate permissions."""
    log_action("contacts", "delete_contact", {"id": contact_id}, {})
    try:
        adb.shell(
            ["content", "delete", "--uri", f"content://contacts/phones/{contact_id}"]
        )
        return MCPResult.success(None)
    except Exception as e:
        return MCPResult.fail(str(e))


"\nmitchell.android.whatsapp\nWhatsApp messaging and reading using Intent + Notification Listener strategy.\n"


def send_message(phone_number: str, text: str) -> MCPResult:
    """
    Send a WhatsApp message by launching the intent.
    Note: If the screen is locked, it may require user interaction to hit send,
    but the text will be pre-filled in the chat.
    Phone number should be in international format (e.g., +1234567890).
    """
    try:
        require_enabled("whatsapp", "send_message")
        encoded_text = urllib.parse.quote(text)
        intent_url = (
            f"https://api.whatsapp.com/send?phone={phone_number}&text={encoded_text}"
        )
        output = adb.shell(
            f"am start -a android.intent.action.VIEW -d '{intent_url}' com.whatsapp"
        )
        if "Error" in output or "Exception" in output:
            return MCPResult.fail(f"Failed to launch WhatsApp: {output}")
        return MCPResult.success(
            f"WhatsApp opened for {phone_number} with pre-filled message."
        )
    except Exception as e:
        return MCPResult.fail(str(e))


def get_recent_chats() -> MCPResult:
    """
    Extract recent WhatsApp senders and messages from the Notification Listener.
    Requires Notification Listener permission.
    """
    try:
        require_enabled("whatsapp", "get_recent_chats")
        notifs_result = get_active_notifications()
        if not notifs_result.ok:
            return notifs_result
        whatsapp_chats = []
        for n in notifs_result.data:
            if n.get("packageName") == "com.whatsapp":
                chat = {
                    "title": n.get("title", "Unknown"),
                    "text": n.get("text", ""),
                    "postTime": n.get("postTime", 0),
                }
                whatsapp_chats.append(chat)
        return MCPResult.success(whatsapp_chats)
    except Exception as e:
        return MCPResult.fail(str(e))


def get_notifications() -> MCPResult:
    """Alias for get_recent_chats."""
    return get_recent_chats()


def search_contact(name: str) -> MCPResult:
    """Search for a contact's WhatsApp number by querying the android.contacts module."""
    try:
        require_enabled("whatsapp", "search_contact")
        res = list_contacts()
        if not res.ok:
            return res
        target_name = name.lower()
        for c in res.data:
            c_name = c.get("display_name", "").lower()
            if target_name in c_name:
                return MCPResult.success(
                    {"name": c.get("display_name"), "number": c.get("number")}
                )
        return MCPResult.fail(f"No contact found matching '{name}'")
    except Exception as e:
        return MCPResult.fail(str(e))


def start_voice_call(contact_name_or_number: str) -> MCPResult:
    """
    Start a WhatsApp voice call.
    Uses the ACCESSIBILITY strategy fallback.
    """
    try:
        require_enabled("whatsapp", "start_voice_call")
        return MCPResult.fail(
            "Accessibility approach deferred as per best practices. Only intent sending is supported."
        )
    except Exception as e:
        return MCPResult.fail(str(e))


"\nAndroid calendar management.\n"


def list_events(start_time: str = None, end_time: str = None):
    """Lists events within a specific time range."""
    try:
        result = adb.shell(
            [
                "content",
                "query",
                "--uri",
                "content://com.android.calendar/events",
                "--projection",
                "_id:title:dtstart:dtend:eventLocation",
            ]
        )
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def add_event(event_data: dict):
    """Adds a new event to the calendar."""
    try:
        title = event_data.get("title", "")
        beginTime = event_data.get("beginTime", "")
        endTime = event_data.get("endTime", "")
        result = adb.shell(
            [
                "am",
                "start",
                "-a",
                "android.intent.action.INSERT",
                "-t",
                "vnd.android.cursor.item/event",
                "--es",
                "title",
                title,
                "--el",
                "beginTime",
                str(beginTime),
                "--el",
                "endTime",
                str(endTime),
            ]
        )
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def delete_event(event_id: str):
    """Deletes a specific calendar event."""
    try:
        result = adb.shell(
            [
                "content",
                "delete",
                "--uri",
                "content://com.android.calendar/events",
                "--where",
                f"_id={event_id}",
            ]
        )
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


# Notification stream tool removed
