"""Unit tests for FastAPI REST API endpoints, web dashboard, and screenshots."""

import unittest
from jarvis.ui.api_server import (
    health_check,
    get_system_status,
    process_user_query,
    list_workflows,
    take_screenshot_endpoint,
    analyze_vision_endpoint,
    get_dashboard_index,
    QueryRequest,
)


class TestUiAndApi(unittest.TestCase):
    """Test suite for FastAPI endpoints and Web Dashboard serving."""

    def test_dashboard_index(self):
        """Verify GET / dashboard HTML file response."""
        resp = get_dashboard_index()
        self.assertIsNotNone(resp)
        self.assertTrue(resp.path.endswith("index.html"))

    def test_health_check_endpoint(self):
        """Verify GET /health response."""
        data = health_check()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "JARVIS")

    def test_status_endpoint(self):
        """Verify GET /status response schema."""
        data = get_system_status()
        self.assertIn("metrics", data)
        self.assertIn("context", data)

    def test_query_endpoint(self):
        """Verify POST /query command execution."""
        req = QueryRequest(query="what is my battery level", session_id="api_test_session")
        data = process_user_query(req)
        self.assertIn("response", data)
        self.assertIn("actions_executed", data)

    def test_workflows_endpoint(self):
        """Verify GET /workflows response."""
        data = list_workflows()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)

    def test_screenshot_and_vision_endpoints(self):
        """Verify screen capture and vision analysis endpoints."""
        ss_res = take_screenshot_endpoint()
        self.assertTrue(ss_res["success"])
        self.assertGreater(ss_res["width"], 0)

        vis_res = analyze_vision_endpoint()
        self.assertTrue(vis_res["success"])
        self.assertIn("analysis", vis_res)


if __name__ == "__main__":
    unittest.main()
