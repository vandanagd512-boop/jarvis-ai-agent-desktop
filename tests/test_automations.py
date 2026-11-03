"""Unit tests for Windows native automation and system monitoring."""

import unittest
from jarvis.monitoring.sys_monitor import (
    BatteryMetrics,
    DiskMetrics,
    MemoryMetrics,
    sys_monitor,
)
from jarvis.automations.windows.window_manager import WindowInfo, window_manager
from jarvis.automations.windows.app_launcher import app_launcher, KNOWN_APPS
from jarvis.automations.windows.media_controls import media_controls
from jarvis.automations.windows.power_manager import power_manager


class TestAutomations(unittest.TestCase):
    """Test suite for system monitor, window manager, and desktop controls."""

    def test_memory_metrics(self):
        """Verify native physical memory metrics retrieval."""
        mem = sys_monitor.get_memory_status()
        self.assertIsInstance(mem, MemoryMetrics)
        self.assertGreater(mem.total_gb, 0.0)
        self.assertGreater(mem.available_gb, 0.0)
        self.assertGreaterEqual(mem.load_percent, 0)
        self.assertLessEqual(mem.load_percent, 100)

    def test_disk_metrics(self):
        """Verify native C: drive free/total space calculations."""
        disk = sys_monitor.get_disk_usage("C:")
        self.assertIsInstance(disk, DiskMetrics)
        self.assertGreater(disk.total_gb, 0.0)
        self.assertGreater(disk.free_gb, 0.0)
        self.assertGreaterEqual(disk.used_percent, 0.0)
        self.assertLessEqual(disk.used_percent, 100.0)

    def test_battery_and_uptime(self):
        """Verify system battery state and uptime reporting."""
        battery = sys_monitor.get_battery_status()
        if battery:
            self.assertIsInstance(battery, BatteryMetrics)
            self.assertIn(battery.is_charging, [True, False])
            self.assertGreaterEqual(battery.percent, 0)
            self.assertLessEqual(battery.percent, 100)

        uptime = sys_monitor.get_system_uptime_seconds()
        self.assertGreater(uptime, 0.0)

    def test_window_manager_enumeration(self):
        """Verify desktop window enumeration."""
        windows = window_manager.list_open_windows(include_empty_titles=True)
        self.assertIsInstance(windows, list)
        for win in windows[:5]:
            self.assertIsInstance(win, WindowInfo)
            self.assertGreater(win.hwnd, 0)

    def test_app_launcher_known_apps(self):
        """Verify app launcher aliases and graceful failure handling."""
        known = app_launcher.list_known_apps()
        self.assertIn("notepad", known)
        self.assertIn("calculator", known)
        self.assertIn("terminal", known)

        # Non-existent app should return error dict rather than raising unhandled exception
        result = app_launcher.launch("non_existent_app_123456_fake")
        self.assertFalse(result["success"])
        self.assertIn("message", result)


if __name__ == "__main__":
    unittest.main()
