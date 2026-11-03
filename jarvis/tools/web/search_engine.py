"""Web search, Wikipedia lookups, and real-time weather service."""

from __future__ import annotations
import urllib.parse
from typing import Any, Dict, List, Optional
import requests
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.WebSearch")


class WebSearchEngine:
    """Provides web search queries, encyclopedic lookups, and weather forecasts."""

    def __init__(self, timeout: float = 6.0) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Query DuckDuckGo Instant Answer API and HTML search."""
        results: List[Dict[str, str]] = []
        try:
            # 1. DuckDuckGo Instant Answer API (JSON)
            api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            resp = requests.get(api_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", "Instant Answer"),
                        "snippet": data["AbstractText"],
                        "url": data.get("AbstractURL", ""),
                    })

                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if "Text" in topic:
                        results.append({
                            "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                            "snippet": topic["Text"],
                            "url": topic.get("FirstURL", ""),
                        })

            return results[:max_results]
        except Exception as exc:
            logger.warning(f"DuckDuckGo search failed or offline: {exc}")
            return []

    def search_wikipedia(self, query: str, sentences: int = 3) -> Dict[str, Any]:
        """Fetch summary of a topic from Wikipedia with strict timeout."""
        try:
            import socket
            import wikipedia
            orig_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.timeout)
            try:
                wikipedia.set_lang("en")
                summary = wikipedia.summary(query, sentences=sentences, auto_suggest=True)
                page = wikipedia.page(query, auto_suggest=True)
                return {
                    "success": True,
                    "title": page.title,
                    "summary": summary,
                    "url": page.url,
                }
            finally:
                socket.setdefaulttimeout(orig_timeout)
        except Exception as exc:
            logger.warning(f"Wikipedia lookup for '{query}' failed: {exc}")
            return {"success": False, "error": str(exc), "query": query}

    def get_weather(self, location: str = "London") -> Dict[str, Any]:
        """Fetch current weather and temperature using wttr.in JSON service."""
        try:
            encoded_loc = urllib.parse.quote(location)
            url = f"https://wttr.in/{encoded_loc}?format=j1"
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                current = data["current_condition"][0]
                temp_c = current.get("temp_C")
                temp_f = current.get("temp_F")
                desc = current.get("weatherDesc", [{}])[0].get("value", "Clear")
                humidity = current.get("humidity")
                wind_kmph = current.get("windspeedKmph")

                return {
                    "success": True,
                    "location": location,
                    "temperature_c": f"{temp_c}°C",
                    "temperature_f": f"{temp_f}°F",
                    "condition": desc,
                    "humidity": f"{humidity}%",
                    "wind_speed": f"{wind_kmph} km/h",
                    "summary": f"Current weather in {location}: {desc}, {temp_c}°C ({temp_f}°F), humidity {humidity}%, wind {wind_kmph} km/h.",
                }
            return {"success": False, "error": f"HTTP status {resp.status_code}"}
        except Exception as exc:
            logger.warning(f"Weather lookup for '{location}' failed or offline: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "summary": f"Weather service is currently unavailable for {location}.",
            }


# Singleton web search engine
web_search = WebSearchEngine()
