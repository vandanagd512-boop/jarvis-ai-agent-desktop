"""Unit tests for JARVIS core foundation modules using unittest."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from jarvis.core.config import Settings
from jarvis.core.events import Event, EventBus, EventType
from jarvis.core.exceptions import JarvisError, ConfigurationError
from jarvis.core.context import SystemContext


class TestCore(unittest.TestCase):
    """Test suite for core configuration, event bus, context, and exceptions."""

    def test_settings_initialization(self):
        """Test configuration defaults and directory creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            settings = Settings(
                DATA_DIR=tmp_path / "data",
                LOG_DIR=tmp_path / "logs",
                PLUGINS_DIR=tmp_path / "plugins",
            )
            settings.ensure_directories()

            self.assertEqual(settings.APP_NAME, "JARVIS")
            self.assertTrue((tmp_path / "data").exists())
            self.assertTrue((tmp_path / "logs").exists())
            self.assertTrue((tmp_path / "plugins").exists())
            self.assertIn("sqlite:///", settings.effective_database_url)

    def test_exception_hierarchy(self):
        """Verify custom exception details string formatting."""
        err = ConfigurationError("Missing key", details={"param": "API_KEY"})
        self.assertIsInstance(err, JarvisError)
        self.assertIn("Missing key", str(err))
        self.assertIn("API_KEY", str(err))

    def test_event_bus_publish_subscribe(self):
        """Verify EventBus dispatch and handling."""
        bus = EventBus()
        received_events = []

        def sample_sync_handler(event: Event):
            received_events.append(event)

        bus.subscribe(EventType.USER_QUERY_RECEIVED, sample_sync_handler)

        test_event = Event(
            event_type=EventType.USER_QUERY_RECEIVED,
            payload={"query": "Hello Jarvis"},
            source="unit_test",
        )

        bus.publish_sync(test_event)

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].payload["query"], "Hello Jarvis")

        # Test unsubscribe
        bus.unsubscribe(EventType.USER_QUERY_RECEIVED, sample_sync_handler)
        received_events.clear()
        bus.publish_sync(test_event)
        self.assertEqual(len(received_events), 0)

    def test_system_context(self):
        """Verify runtime context serialization."""
        ctx = SystemContext()
        ctx.active_window_title = "VS Code - main.py"
        ctx.battery_percent = 85.0
        data = ctx.to_dict()

        self.assertIn("Windows", data["os"])
        self.assertEqual(data["active_window"], "VS Code - main.py")
        self.assertEqual(data["battery"], "85%")


if __name__ == "__main__":
    unittest.main()
