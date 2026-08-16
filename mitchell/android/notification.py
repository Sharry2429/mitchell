"""
mitchell.android.notification
Android notifications management.
"""

from mitchell.android import adb
from mitchell.core.result import MCPResult


def get_active_notifications() -> MCPResult:
    """Gets currently active notifications by dumping notification service state."""
    try:
        output = adb.shell("dumpsys notification --noredact")
        # Basic parsing: look for lines with 'NotificationRecord' or similar.
        # This is a simplified extraction since dumpsys is very unstructured.
        records = []
        for line in output.splitlines():
            if "NotificationRecord{" in line:
                records.append(line.strip())
        return MCPResult.success(records)
    except Exception as e:
        return MCPResult.error(f"Failed to get notifications: {e}")
