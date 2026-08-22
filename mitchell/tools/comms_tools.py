"""Communication tools for the Mitchell ToolRegistry exposing WhatsApp MCP, SMS, and Unified Hub."""

import json
from typing import Any, Dict, List, Optional

from mitchell.comms import communication_hub, message_scheduler, sms_manager, whatsapp_bridge, whatsapp_mcp
from mitchell.tools.registry import Tool


def tool_comms_send_whatsapp(phone_number: str, message: str) -> str:
    """Send a WhatsApp message via WhatsApp MCP or Web intent."""
    res = whatsapp_bridge.send_whatsapp_message(phone_number=phone_number, text=message)
    return json.dumps(res)


def tool_comms_whatsapp_mcp_list_chats(limit: int = 15) -> str:
    """List recent WhatsApp conversations via WhatsApp MCP."""
    chats = whatsapp_mcp.list_chats(limit=limit)
    return json.dumps(chats, indent=2)


def tool_comms_whatsapp_mcp_list_messages(chat_jid: str, limit: int = 20) -> str:
    """List messages from a WhatsApp chat via WhatsApp MCP."""
    messages = whatsapp_mcp.list_messages(chat_jid=chat_jid, limit=limit)
    return json.dumps(messages, indent=2)


def tool_comms_whatsapp_mcp_search_contacts(query: str) -> str:
    """Search WhatsApp contacts by name or phone number via WhatsApp MCP."""
    contacts = whatsapp_mcp.search_contacts(query=query)
    return json.dumps(contacts, indent=2)


def tool_comms_whatsapp_mcp_send_media(recipient: str, media_path: str, caption: str = "") -> str:
    """Send an image, document, or media file to a WhatsApp contact via WhatsApp MCP."""
    res = whatsapp_mcp.send_media(recipient=recipient, media_path=media_path, caption=caption)
    return json.dumps(res)


def tool_comms_list_inbox(channel: Optional[str] = None) -> str:
    """List recent messages across WhatsApp, SMS, and Email in the unified hub."""
    msgs = communication_hub.list_messages(channel=channel, limit=10)
    return json.dumps(msgs, indent=2)


# Tool definitions
whatsapp_tool = Tool(
    name="comms_send_whatsapp",
    description="Send a message to a contact via WhatsApp MCP (https://github.com/lharries/whatsapp-mcp).",
    parameters={
        "type": "object",
        "properties": {
            "phone_number": {"type": "string", "description": "Phone number with country code (e.g. +1234567890)"},
            "message": {"type": "string", "description": "Message text"},
        },
        "required": ["phone_number", "message"],
    },
    function=tool_comms_send_whatsapp,
)

whatsapp_list_chats_tool = Tool(
    name="comms_whatsapp_list_chats",
    description="List active WhatsApp conversations with latest message summaries via WhatsApp MCP.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max chats to retrieve (default: 15)"},
        },
    },
    function=tool_comms_whatsapp_mcp_list_chats,
)

whatsapp_list_messages_tool = Tool(
    name="comms_whatsapp_list_messages",
    description="Retrieve message history from a specific WhatsApp chat or contact.",
    parameters={
        "type": "object",
        "properties": {
            "chat_jid": {"type": "string", "description": "Chat JID or contact phone number"},
            "limit": {"type": "integer", "description": "Max messages to retrieve"},
        },
        "required": ["chat_jid"],
    },
    function=tool_comms_whatsapp_mcp_list_messages,
)

whatsapp_search_contacts_tool = Tool(
    name="comms_whatsapp_search_contacts",
    description="Search WhatsApp address book and contacts by name or phone number.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Contact name or phone query"},
        },
        "required": ["query"],
    },
    function=tool_comms_whatsapp_mcp_search_contacts,
)

whatsapp_send_media_tool = Tool(
    name="comms_whatsapp_send_media",
    description="Send a media file, image, or document to a WhatsApp contact.",
    parameters={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Recipient phone number or JID"},
            "media_path": {"type": "string", "description": "Local file path to media"},
            "caption": {"type": "string", "description": "Optional caption"},
        },
        "required": ["recipient", "media_path"],
    },
    function=tool_comms_whatsapp_mcp_send_media,
)

inbox_tool = Tool(
    name="comms_get_unified_inbox",
    description="Retrieve aggregated recent messages across WhatsApp, SMS, and Email channels.",
    parameters={
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "Optional channel filter: 'whatsapp', 'sms', 'email'"}
        },
    },
    function=tool_comms_list_inbox,
)

TOOLS = [
    whatsapp_tool,
    whatsapp_list_chats_tool,
    whatsapp_list_messages_tool,
    whatsapp_search_contacts_tool,
    whatsapp_send_media_tool,
    inbox_tool,
]
