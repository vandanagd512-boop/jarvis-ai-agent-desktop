"""Plugin manager for dynamic discovery, lifecycle, and tool registration."""

from __future__ import annotations
import importlib.util
import inspect
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from jarvis.brain.router import action_router
from jarvis.core.config import get_settings
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.logger import get_logger
from jarvis.plugins.base_plugin import BasePlugin, PluginTool

logger = get_logger("JARVIS.PluginManager")


class PluginManager:
    """Manages the discovery, loading, and lifecycle of extension plugins."""

    def __init__(self, plugins_dir: Optional[Path] = None) -> None:
        self.settings = get_settings()
        self.plugins_dir = plugins_dir or self.settings.PLUGINS_DIR
        self._loaded_plugins: Dict[str, BasePlugin] = {}
        self._plugin_tools: Dict[str, PluginTool] = {}

    def discover_and_load_all(self) -> List[str]:
        """Scan plugins directory and load all valid plugins."""
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        loaded_names = []

        for item in self.plugins_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                plugin = self._load_plugin_from_file(item)
                if plugin:
                    loaded_names.append(plugin.name)

        logger.info(f"Loaded {len(loaded_names)} plugins: {loaded_names}")
        return loaded_names

    def _load_plugin_from_file(self, file_path: Path) -> Optional[BasePlugin]:
        """Dynamically import a python module and instantiate BasePlugin subclass."""
        module_name = f"jarvis_plugin_{file_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find BasePlugin subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    inspect.isclass(attr)
                    and issubclass(attr, BasePlugin)
                    and attr is not BasePlugin
                ):
                    plugin_instance: BasePlugin = attr()
                    self.register_plugin(plugin_instance)
                    return plugin_instance

        except Exception as exc:
            logger.error(f"Failed to load plugin from '{file_path}': {exc}", exc_info=True)
            return None
        return None

    def register_plugin(self, plugin: BasePlugin) -> bool:
        """Register, initialize, and wire tools/events for a plugin instance."""
        try:
            plugin.on_load()
            plugin.is_enabled = True
            self._loaded_plugins[plugin.name] = plugin

            # Register tools with ActionRouter
            for tool in plugin.get_tools():
                self._plugin_tools[tool.name] = tool
                action_router.register_tool(tool.name, tool.handler)
                logger.info(f"Registered plugin tool: '{tool.name}' from '{plugin.name}'")

            # Register event listeners with EventBus
            for ev_type, handler in plugin.get_event_listeners().items():
                event_bus.subscribe(ev_type, handler)

            event_bus.publish_sync(
                Event(
                    event_type=EventType.PLUGIN_LOADED,
                    payload={"plugin": plugin.name, "version": plugin.version},
                )
            )
            return True
        except Exception as exc:
            logger.error(f"Error initializing plugin '{plugin.name}': {exc}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload plugin, remove tools and event listeners."""
        plugin = self._loaded_plugins.get(plugin_name)
        if not plugin:
            return False

        try:
            plugin.on_unload()
            plugin.is_enabled = False

            # Unsubscribe listeners
            for ev_type, handler in plugin.get_event_listeners().items():
                event_bus.unsubscribe(ev_type, handler)

            del self._loaded_plugins[plugin_name]
            event_bus.publish_sync(
                Event(
                    event_type=EventType.PLUGIN_UNLOADED,
                    payload={"plugin": plugin_name},
                )
            )
            logger.info(f"Successfully unloaded plugin: '{plugin_name}'")
            return True
        except Exception as exc:
            logger.error(f"Error unloading plugin '{plugin_name}': {exc}")
            return False

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all active plugins."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "author": p.author,
                "description": p.description,
                "is_enabled": p.is_enabled,
                "tools": [t.name for t in p.get_tools()],
            }
            for p in self._loaded_plugins.values()
        ]


# Singleton plugin manager
plugin_manager = PluginManager()
