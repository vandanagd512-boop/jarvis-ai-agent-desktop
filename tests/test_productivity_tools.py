"""Unit tests for Productivity, File Manager, and Developer tools."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from jarvis.tools.file_manager.file_ops import FileManager
from jarvis.tools.productivity.calendar_manager import CalendarManager, parse_natural_datetime
from jarvis.tools.developer.code_runner import CodeRunner


class TestProductivityTools(unittest.TestCase):
    """Test suite for file operations, calendar parsing, and code sandbox execution."""

    def test_file_operations(self):
        """Verify file creation, reading, searching, checksumming, and organization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            fm = FileManager()
            tmp_path = Path(tmp_dir)

            # Write file
            test_file = tmp_path / "sample.py"
            write_res = fm.write_file_content(str(test_file), "print('Hello from test file')\n")
            self.assertTrue(write_res["success"])
            self.assertTrue(test_file.exists())

            # Read file
            read_res = fm.read_file_content(str(test_file))
            self.assertTrue(read_res["success"])
            self.assertIn("Hello from test file", read_res["content"])

            # Search file
            search_res = fm.search_files(str(tmp_path), pattern="*.py")
            self.assertEqual(len(search_res), 1)
            self.assertEqual(search_res[0]["name"], "sample.py")

            # Checksum
            hash_res = fm.calculate_file_checksum(str(test_file), algorithm="sha256")
            self.assertTrue(hash_res["success"])
            self.assertEqual(len(hash_res["checksum"]), 64)

            # Organize directory
            org_res = fm.organize_directory(str(tmp_path))
            self.assertTrue(org_res["success"])
            self.assertTrue((tmp_path / "Code" / "sample.py").exists())

    def test_calendar_natural_date_parsing(self):
        """Verify relative natural date expression parsing."""
        now = datetime.now(timezone.utc)

        # "in 45 minutes"
        dt_mins = parse_natural_datetime("in 45 minutes")
        self.assertIsNotNone(dt_mins)
        diff_mins = (dt_mins - now).total_seconds() / 60
        self.assertAlmostEqual(diff_mins, 45, delta=2)

        # "in 3 hours"
        dt_hrs = parse_natural_datetime("in 3 hours")
        self.assertIsNotNone(dt_hrs)
        diff_hrs = (dt_hrs - now).total_seconds() / 3600
        self.assertAlmostEqual(diff_hrs, 3, delta=0.1)

        # "tomorrow"
        dt_tom = parse_natural_datetime("tomorrow at 4pm")
        self.assertIsNotNone(dt_tom)
        self.assertEqual(dt_tom.hour, 16)

    def test_code_runner_execution(self):
        """Verify sandboxed Python script execution."""
        runner = CodeRunner(default_timeout=5)
        snippet = "x = 10 * 5\nprint(f'CALCULATED_{x}')"
        res = runner.run_python(snippet)
        self.assertTrue(res["success"])
        self.assertIn("CALCULATED_50", res["stdout"])
        self.assertEqual(res["exit_code"], 0)

    def test_whatsapp_client_actions(self):
        """Verify WhatsApp client message and call preparation."""
        from jarvis.tools.productivity.whatsapp_client import whatsapp_client
        res_msg = whatsapp_client.send_message("9999999999", "Test Hello")
        self.assertTrue(res_msg["success"])
        self.assertIn("9999999999", res_msg["phone"])

        res_call = whatsapp_client.initiate_call("9999999999")
        self.assertTrue(res_call["success"])


if __name__ == "__main__":
    unittest.main()
