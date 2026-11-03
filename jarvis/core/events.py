"""Asynchronous typed Event Bus for JARVIS.

Enables decoupled, publish-subscribe event communication across all subsystems:
voice, automations, plugins, memory, monitoring, and UI.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import inspect
from typing import Any, Awaitable, Callable, Dict, List
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.Events")


class EventType(str, Enum):
    """Core event types emitted across JARVIS."""
    # Lifecycle
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"

    # Voice / Audio
    WAKE_WORD_DETECTED = "voice.wake_word_detected"
    SPEECH_RECORDING_STARTED = "voice.speech_recording_started"
    SPEECH_RECORDING_ENDED = "voice.speech_recording_ended"
    SPEECH_TRANSCRIBED = "voice.speech_transcribed"
    TTS_STARTED = "voice.tts_started"
    TTS_FINISHED = "voice.tts_finished"

    # Brain & Reasoning
    USER_QUERY_RECEIVED = "brain.user_query_received"
    AI_RESPONSE_GENERATED = "brain.ai_response_generated"
    TOOL_EXECUTION_REQUESTED = "brain.tool_execution_requested"
    TOOL_EXECUTION_COMPLETED = "brain.tool_execution_completed"
    TOOL_EXECUTION_FAILED = "brain.tool_execution_failed"

    # Windows Automation & System
    WINDOW_FOCUSED = "system.window_focused"
    MEDIA_ACTION_TRIGGERED = "system.media_action"
    SYSTEM_METRICS_UPDATED = "system.metrics_updated"
    SYSTEM_ALERT = "system.alert"

    # Clipboard & Vision
    CLIPBOARD_CHANGED = "clipboard.changed"
    SCREENSHOT_TAKEN = "vision.screenshot_taken"

    # Workflows & Plugins
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_FINISHED = "workflow.finished"
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"


@dataclass
class Event:
    """Event envelope containing metadata and typed payload."""
    event_type: EventType | str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "core"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return self.event_type.value if isinstance(self.event_type, Enum) else str(self.event_type)


EventHandler = Callable[[Event], Any | Awaitable[Any]]


class EventBus:
    """Thread-safe, asynchronous event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def subscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        """Register a handler for a given event type."""
        key = event_type.value if isinstance(event_type, Enum) else str(event_type)
        if key not in self._subscribers:
            self._subscribers[key] = []
        if handler not in self._subscribers[key]:
            self._subscribers[key].append(handler)
            logger.debug(f"Subscribed handler '{handler.__name__}' to event '{key}'")

    def unsubscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        """Unregister a handler for a given event type."""
        key = event_type.value if isinstance(event_type, Enum) else str(event_type)
        if key in self._subscribers and handler in self._subscribers[key]:
            self._subscribers[key].remove(handler)
            logger.debug(f"Unsubscribed handler '{handler.__name__}' from event '{key}'")

    async def publish(self, event: Event) -> None:
        """Publish an event asynchronously to all registered subscribers."""
        key = event.name
        handlers = list(self._subscribers.get(key, []))
        # Also notify wildcard subscribers if any
        handlers.extend(self._subscribers.get("*", []))

        if not handlers:
            return

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error(
                    f"Error in event handler '{handler.__name__}' for event '{key}': {exc}",
                    exc_info=True,
                )

    def publish_sync(self, event: Event) -> None:
        """Publish an event synchronously to all registered subscribers."""
        key = event.name
        handlers = list(self._subscribers.get(key, []))
        handlers.extend(self._subscribers.get("*", []))

        if not handlers:
            return

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        pass
                else:
                    handler(event)
            except Exception as exc:
                logger.error(
                    f"Error in event handler '{handler.__name__}' for event '{key}': {exc}",
                    exc_info=True,
                )


# Singleton event bus instance
event_bus = EventBus()
