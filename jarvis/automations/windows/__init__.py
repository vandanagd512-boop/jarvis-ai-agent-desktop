"""Windows desktop automations and control subsystem."""

from jarvis.automations.windows.app_launcher import AppLauncher, app_launcher
from jarvis.automations.windows.media_controls import MediaControls, media_controls
from jarvis.automations.windows.power_manager import PowerManager, power_manager
from jarvis.automations.windows.window_manager import (
    WindowInfo,
    WindowManager,
    window_manager,
)

__all__ = [
    "WindowManager",
    "window_manager",
    "WindowInfo",
    "MediaControls",
    "media_controls",
    "PowerManager",
    "power_manager",
    "AppLauncher",
    "app_launcher",
]
