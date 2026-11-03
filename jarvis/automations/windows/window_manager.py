"""Windows window management and control using Win32 API."""

from __future__ import annotations
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.WindowManager")

user32 = ctypes.windll.user32

# Win32 Constants
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_RESTORE = 9
WM_CLOSE = 0x0010


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    pid: int
    is_visible: bool


class WindowManager:
    """Provides focus, minimize, maximize, and query controls for Windows desktop windows."""

    def __init__(self) -> None:
        self.user32 = user32

    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Retrieve details of the current active foreground window."""
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None

        title = self._get_window_title(hwnd)
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return WindowInfo(
            hwnd=hwnd,
            title=title,
            pid=pid.value,
            is_visible=bool(self.user32.IsWindowVisible(hwnd)),
        )

    def _get_window_title(self, hwnd: int) -> str:
        """Read window title string from HWND."""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buff = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value

    def list_open_windows(self, include_empty_titles: bool = False) -> List[WindowInfo]:
        """List all top-level visible desktop application windows."""
        windows: List[WindowInfo] = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def enum_callback(hwnd, lparam):
            if self.user32.IsWindowVisible(hwnd):
                title = self._get_window_title(hwnd).strip()
                if title or include_empty_titles:
                    pid = wintypes.DWORD()
                    self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    windows.append(
                        WindowInfo(
                            hwnd=hwnd,
                            title=title,
                            pid=pid.value,
                            is_visible=True,
                        )
                    )
            return True

        self.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return windows

    def find_window_by_title(self, title_query: str) -> Optional[WindowInfo]:
        """Find the first window whose title matches title_query (case-insensitive substring)."""
        query = title_query.strip().lower()
        windows = self.list_open_windows()
        for win in windows:
            if query in win.title.lower():
                return win
        return None

    def focus_window(self, title_query: str) -> bool:
        """Bring window matching title_query to the foreground."""
        win = self.find_window_by_title(title_query)
        if not win:
            logger.warning(f"Window matching '{title_query}' not found.")
            return False

        # Restore if minimized
        self.user32.ShowWindow(win.hwnd, SW_RESTORE)
        # Bring to foreground
        success = bool(self.user32.SetForegroundWindow(win.hwnd))
        logger.info(f"Focus window '{win.title}' (HWND {win.hwnd}): {success}")
        return success

    def minimize_window(self, title_query: str) -> bool:
        """Minimize window matching title_query."""
        win = self.find_window_by_title(title_query)
        if not win:
            return False
        return bool(self.user32.ShowWindow(win.hwnd, SW_SHOWMINIMIZED))

    def maximize_window(self, title_query: str) -> bool:
        """Maximize window matching title_query."""
        win = self.find_window_by_title(title_query)
        if not win:
            return False
        return bool(self.user32.ShowWindow(win.hwnd, SW_MAXIMIZE))

    def close_window(self, title_query: str) -> bool:
        """Send WM_CLOSE signal to close window."""
        win = self.find_window_by_title(title_query)
        if not win:
            return False
        logger.info(f"Sending WM_CLOSE to window '{win.title}'")
        return bool(self.user32.PostMessageW(win.hwnd, WM_CLOSE, 0, 0))


# Singleton instance
window_manager = WindowManager()
