"""Unit tests for Plugin Architecture and Multi-Step Workflow Engine."""

from pathlib import Path
import unittest

from jarvis.plugins.plugin_manager import plugin_manager
from jarvis.workflow.workflow_engine import (
    WorkflowDefinition,
    WorkflowStep,
    workflow_engine,
)
from jarvis.brain.router import action_router


class TestPluginsAndWorkflows(unittest.TestCase):
    """Test suite for dynamic plugin lifecycle and multi-step workflow execution."""

    def test_plugin_discovery_and_execution(self):
        """Verify discovery of plugins and tool registration in action router."""
        loaded = plugin_manager.discover_and_load_all()
        self.assertIn("CalculatorPlugin", loaded)

        # Verify tool is available in router
        self.assertIn("calculate", action_router._tools)

        # Execute tool via router
        calc_tool = action_router._tools["calculate"]
        calc_res = calc_tool(expression="sqrt(144) + 25")
        self.assertTrue(calc_res["success"])
        self.assertEqual(calc_res["result"], 37.0)

        # Unload plugin
        unloaded = plugin_manager.unload_plugin("CalculatorPlugin")
        self.assertTrue(unloaded)

    def test_workflow_orchestration(self):
        """Verify multi-step workflow with variable propagation and step execution."""
        custom_wf = WorkflowDefinition(
            workflow_id="test_custom_routine",
            name="Test Custom Routine",
            description="Testing sequential step chaining and variables",
            steps=[
                WorkflowStep(
                    step_id="step_1",
                    tool_name="get_memory_status",
                    save_as="mem_data",
                ),
                WorkflowStep(
                    step_id="step_2",
                    tool_name="create_note",
                    arguments={
                        "title": "RAM Audit Note",
                        "content": "System RAM load: ${mem_data}",
                        "tags": "test,audit",
                    },
                ),
            ],
        )

        workflow_engine.register_workflow(custom_wf)
        res = workflow_engine.execute_workflow("test_custom_routine")

        self.assertTrue(res["success"])
        self.assertEqual(res["workflow"], "Test Custom Routine")
        self.assertEqual(len(res["step_results"]), 2)
        self.assertEqual(res["step_results"][0]["status"], "success")
        self.assertEqual(res["step_results"][1]["status"], "success")
        self.assertIn("mem_data", res["variables"])


if __name__ == "__main__":
    unittest.main()
