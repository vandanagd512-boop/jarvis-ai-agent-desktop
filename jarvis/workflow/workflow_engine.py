"""Multi-step workflow automation engine with variable propagation and audit logs."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional
from jarvis.brain.router import action_router
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.logger import get_logger
from jarvis.memory.database import get_db_session
from jarvis.memory.models import ExecutionAuditLog

logger = get_logger("JARVIS.WorkflowEngine")


@dataclass
class WorkflowStep:
    """Represents a single step in an automated multi-step workflow."""
    step_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    save_as: Optional[str] = None
    condition: Optional[str] = None  # Optional expression evaluating to True/False


@dataclass
class WorkflowDefinition:
    """Definition of an automated routine or macro."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)


class WorkflowEngine:
    """Executes multi-step workflows, resolving dynamic variables and logging execution."""

    def __init__(self) -> None:
        self._workflows: Dict[str, WorkflowDefinition] = {}

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[workflow.workflow_id] = workflow
        logger.info(f"Registered workflow: '{workflow.name}' ({workflow.workflow_id})")

    def execute_workflow(
        self,
        workflow_id_or_def: str | WorkflowDefinition,
        initial_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute all steps sequentially in a workflow with variable substitution."""
        if isinstance(workflow_id_or_def, str):
            wf = self._workflows.get(workflow_id_or_def)
            if not wf:
                return {"success": False, "error": f"Workflow '{workflow_id_or_def}' not found."}
        else:
            wf = workflow_id_or_def

        t0 = time.time()
        logger.info(f"Starting execution of workflow: '{wf.name}'")
        event_bus.publish_sync(
            Event(event_type=EventType.WORKFLOW_STARTED, payload={"workflow": wf.name})
        )

        variables: Dict[str, Any] = dict(initial_variables or {})
        step_results: List[Dict[str, Any]] = []

        for step in wf.steps:
            # Check condition if present
            if step.condition and not self._evaluate_condition(step.condition, variables):
                logger.info(f"Skipping step '{step.step_id}' - condition '{step.condition}' false.")
                continue

            # Resolve variables in arguments
            resolved_args = self._resolve_arguments(step.arguments, variables)

            handler = action_router._tools.get(step.tool_name)
            if not handler:
                err_msg = f"Tool '{step.tool_name}' in step '{step.step_id}' not found."
                logger.error(err_msg)
                return {
                    "success": False,
                    "workflow": wf.name,
                    "failed_step": step.step_id,
                    "error": err_msg,
                    "step_results": step_results,
                }

            s_t0 = time.time()
            try:
                result = handler(**resolved_args) if resolved_args else handler()
                s_dur = round((time.time() - s_t0) * 1000, 2)

                if step.save_as:
                    variables[step.save_as] = result

                step_results.append({
                    "step_id": step.step_id,
                    "tool": step.tool_name,
                    "status": "success",
                    "duration_ms": s_dur,
                    "result": result,
                })
                event_bus.publish_sync(
                    Event(
                        event_type=EventType.WORKFLOW_STEP_COMPLETED,
                        payload={"step": step.step_id, "tool": step.tool_name},
                    )
                )
            except Exception as exc:
                s_dur = round((time.time() - s_t0) * 1000, 2)
                logger.error(f"Error in step '{step.step_id}': {exc}", exc_info=True)
                step_results.append({
                    "step_id": step.step_id,
                    "tool": step.tool_name,
                    "status": "error",
                    "duration_ms": s_dur,
                    "error": str(exc),
                })
                # Terminate workflow on error
                return {
                    "success": False,
                    "workflow": wf.name,
                    "failed_step": step.step_id,
                    "error": str(exc),
                    "step_results": step_results,
                }

        total_dur = round((time.time() - t0) * 1000, 2)

        # Log execution in database audit log
        try:
            with get_db_session() as session:
                log = ExecutionAuditLog(
                    action_name=f"Workflow:{wf.name}",
                    parameters_json=json.dumps(initial_variables or {}),
                    status="success",
                    result_preview=f"Executed {len(step_results)} steps successfully.",
                    duration_ms=total_dur,
                )
                session.add(log)
        except Exception:
            pass

        event_bus.publish_sync(
            Event(event_type=EventType.WORKFLOW_FINISHED, payload={"workflow": wf.name})
        )
        logger.info(f"Workflow '{wf.name}' completed in {total_dur}ms")
        return {
            "success": True,
            "workflow": wf.name,
            "total_duration_ms": total_dur,
            "step_results": step_results,
            "variables": variables,
        }

    def _resolve_arguments(self, args: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute ${var_name} placeholders in arguments."""
        resolved = {}
        for k, v in args.items():
            if isinstance(v, str):
                match = re.match(r"^\$\{([a-zA-Z0-9_\.]+)\}$", v.strip())
                if match:
                    var_name = match.group(1)
                    resolved[k] = variables.get(var_name, v)
                else:
                    # String interpolation
                    def replace_fn(m):
                        return str(variables.get(m.group(1), m.group(0)))
                    resolved[k] = re.sub(r"\$\{([a-zA-Z0-9_\.]+)\}", replace_fn, v)
            else:
                resolved[k] = v
        return resolved

    def _evaluate_condition(self, condition_expr: str, variables: Dict[str, Any]) -> bool:
        """Safely evaluate boolean condition against current variables."""
        try:
            return bool(eval(condition_expr, {"__builtins__": {}}, variables))
        except Exception:
            return True


# Singleton workflow engine instance
workflow_engine = WorkflowEngine()
