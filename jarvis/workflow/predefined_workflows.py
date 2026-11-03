"""Built-in production workflows and multi-step macros for JARVIS."""

from jarvis.workflow.workflow_engine import (
    WorkflowDefinition,
    WorkflowStep,
    workflow_engine,
)


def register_predefined_workflows() -> None:
    """Register default out-of-the-box routines."""

    # 1. Morning System Briefing
    morning_wf = WorkflowDefinition(
        workflow_id="morning_briefing",
        name="Morning System Briefing",
        description="Queries system metrics, hardware status, and logs a daily briefing note.",
        steps=[
            WorkflowStep(
                step_id="step_sys_status",
                tool_name="get_system_summary",
                save_as="sys_summary",
            ),
            WorkflowStep(
                step_id="step_create_briefing_note",
                tool_name="create_note",
                arguments={
                    "title": "Daily Briefing Note",
                    "content": "Automated morning checklist executed. System healthy.",
                    "tags": "daily,briefing",
                },
            ),
        ],
    )
    workflow_engine.register_workflow(morning_wf)

    # 2. Focus Work Mode
    focus_wf = WorkflowDefinition(
        workflow_id="focus_mode",
        name="Focus Work Mode",
        description="Lowers background volume and records focus session start.",
        steps=[
            WorkflowStep(
                step_id="step_lower_volume",
                tool_name="volume_down",
                arguments={"steps": 4},
            ),
            WorkflowStep(
                step_id="step_focus_note",
                tool_name="create_note",
                arguments={
                    "title": "Focus Mode Active",
                    "content": "Focus mode initiated. Distractions suppressed.",
                    "tags": "focus,productivity",
                },
            ),
        ],
    )
    workflow_engine.register_workflow(focus_wf)


# Auto-register upon import
register_predefined_workflows()
