"""Mitchell Studio — Absolute Command Center.

Complete unified surface providing chat, workspace, IDE, media, devices, 
agents, memory, providers, and all other command panels.
"""

from mitchell.studio.server import (
    MitchellStudioServer,
    StudioStateProvider,
    create_studio_app,
    studio_app,
    studio_state,
    ws_manager,
)

__all__ = [
    "MitchellStudioServer",
    "StudioStateProvider",
    "create_studio_app",
    "studio_app",
    "studio_state",
    "ws_manager",
]
