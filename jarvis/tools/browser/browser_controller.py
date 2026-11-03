"""Browser control and automated web navigation."""

from __future__ import annotations
import urllib.parse
import webbrowser
from typing import Any, Dict
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.Browser")


class BrowserController:
    """Automates web browser opening, URL navigation, and web searches."""

    def open_url(self, url: str, new_window: bool = False) -> Dict[str, Any]:
        """Navigate to a URL in the system's default web browser."""
        target_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
        logger.info(f"Opening URL in browser: {target_url}")
        try:
            success = webbrowser.open(target_url, new=1 if new_window else 2)
            return {
                "success": success,
                "url": target_url,
                "message": f"Opened {target_url} in default browser.",
            }
        except Exception as exc:
            logger.error(f"Failed to open browser URL '{url}': {exc}")
            return {"success": False, "error": str(exc)}

    def search_web(self, query: str, engine: str = "google") -> Dict[str, Any]:
        """Open web search query in browser."""
        encoded = urllib.parse.quote(query)
        if engine.lower() == "duckduckgo":
            url = f"https://duckduckgo.com/?q={encoded}"
        elif engine.lower() == "bing":
            url = f"https://www.bing.com/search?q={encoded}"
        else:
            url = f"https://www.google.com/search?q={encoded}"

        return self.open_url(url)


# Singleton browser controller
browser_controller = BrowserController()
