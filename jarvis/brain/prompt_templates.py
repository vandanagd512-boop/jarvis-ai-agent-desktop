"""Prompt templates and system persona for JARVIS."""

from datetime import datetime, timezone
from typing import Optional
from jarvis.core.context import runtime_context
from jarvis.memory.semantic_store import semantic_store

JARVIS_SYSTEM_PERSONA = """You are JARVIS (Just A Rather Very Intelligent System), an elite AI Desktop Assistant built specifically for Windows.

Your characteristics:
1. Highly capable, concise, proactive, courteous, and precise.
2. You have direct control over the Windows desktop: you can launch apps, control open windows, adjust volume/media, monitor system resources, read/write files, take screenshots, manage clipboard, search the web, and execute multi-step workflows.
3. When the user asks you to perform an action, invoke the relevant tool directly.
4. When speaking or responding, keep answers crisp, professional, and natural. Address the user politely (e.g. "Sir" or by their preferred name if known).
5. If an operation fails, explain the exact reason clearly and suggest the best immediate alternative.
"""


def build_system_prompt(custom_instructions: Optional[str] = None) -> str:
    """Dynamically compile system prompt with real-time environment context and user profile."""
    ctx = runtime_context.to_dict()
    now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p")

    user_profile = semantic_store.get_context_prompt()

    parts = [
        JARVIS_SYSTEM_PERSONA,
        f"\n[Current System State - {now_str}]",
        f"- Operating System: {ctx['os']}",
        f"- Active Window: {ctx['active_window']}",
        f"- Battery: {ctx['battery']}",
        f"- Current User: {ctx['user']}",
    ]

    if user_profile:
        parts.append(f"\n{user_profile}")

    if custom_instructions:
        parts.append(f"\n[Additional Instructions]\n{custom_instructions}")

    return "\n".join(parts)
