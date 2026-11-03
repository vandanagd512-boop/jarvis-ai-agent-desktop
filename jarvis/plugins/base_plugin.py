"""Abstract base class and contracts for JARVIS plugins."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from jarvis.core.events import EventHandler, EventType


@dataclass
class PluginTool:
    """Represents a tool exposed by a plugin."""
    name: str
    description: str
    handler: Callable[..., Any]
    parameters_schema: Dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """Abstract base class for all extensible JARVIS plugins."""

    name: str = "BasePlugin"
    version: str = "1.0.0"
    author: str = "JARVIS Developer"
    description: str = "Base plugin description"

    def __init__(self) -> None:
        self.is_enabled: bool = False

    @abstractmethod
    def on_load(self) -> None:
        """Called when plugin is loaded and initialized."""
        pass

    @abstractmethod
    def on_unload(self) -> None:
        """Called before plugin is unloaded for clean resource tear-down."""
        pass

    def get_tools(self) -> List[PluginTool]:
        """Return list of executable tools exposed to the reasoning engine."""
        return []

    def get_event_listeners(self) -> Dict[EventType | str, EventHandler]:
        """Return event subscriptions provided by this plugin."""
        return {}
