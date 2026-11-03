"""Intelligent reasoning router and action executor for JARVIS."""

from __future__ import annotations
import inspect
from typing import Any, Callable, Dict, List, Optional
from jarvis.brain.gemini_provider import GeminiProvider
from jarvis.brain.llm_provider import BaseLLMProvider, LLMResponse, ToolCall
from jarvis.brain.offline_provider import OfflineProvider
from jarvis.brain.openai_provider import OpenAIProvider
from jarvis.brain.prompt_templates import build_system_prompt
from jarvis.core.config import get_settings
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.exceptions import BrainError
from jarvis.core.logger import get_logger

# Import automation handlers for tool dispatch
from jarvis.automations.windows.app_launcher import app_launcher
from jarvis.automations.windows.media_controls import media_controls
from jarvis.automations.windows.power_manager import power_manager
from jarvis.automations.windows.window_manager import window_manager
from jarvis.memory.conversation_store import conversation_store
from jarvis.memory.semantic_store import semantic_store
from jarvis.monitoring.sys_monitor import sys_monitor
from jarvis.tools.developer.code_runner import code_runner

logger = get_logger("JARVIS.Router")


class ActionRouter:
    """Routes user queries to the appropriate reasoning engine and executes tool calls."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.offline_provider = OfflineProvider()
        self.gemini_provider = GeminiProvider()
        self.openai_provider = OpenAIProvider()
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._query_cache: Dict[str, Any] = {}

        self._register_native_tools()

    def _register_native_tools(self) -> None:
        """Register built-in desktop automations in the tool dispatch registry."""
        self.register_tool("launch_app", lambda target, arguments=None: app_launcher.launch(target, arguments))
        self.register_tool("close_window", lambda title_query="": window_manager.close_window(title_query))
        self.register_tool("focus_window", lambda title_query="": window_manager.focus_window(title_query))
        self.register_tool("minimize_window", lambda title_query="": window_manager.minimize_window(title_query))
        self.register_tool("maximize_window", lambda title_query="": window_manager.maximize_window(title_query))

        self.register_tool("volume_up", lambda steps=2: media_controls.volume_up(steps))
        self.register_tool("volume_down", lambda steps=2: media_controls.volume_down(steps))
        self.register_tool("toggle_mute", lambda: media_controls.toggle_mute())
        self.register_tool("media_play_pause", lambda: media_controls.play_pause())
        self.register_tool("media_next", lambda: media_controls.next_track())
        self.register_tool("media_previous", lambda: media_controls.prev_track())
        self.register_tool("refresh_page", lambda: media_controls.refresh_page())

        self.register_tool("get_battery_status", lambda: sys_monitor.get_battery_status())
        self.register_tool("get_memory_status", lambda: sys_monitor.get_memory_status())
        self.register_tool("get_disk_usage", lambda drive="C:": sys_monitor.get_disk_usage(drive))
        self.register_tool("get_system_summary", lambda: sys_monitor.get_summary())

        self.register_tool("lock_workstation", lambda: power_manager.lock_workstation())
        self.register_tool("create_note", lambda title, content, tags="": semantic_store.create_note(title, content, tags))
        self.register_tool("run_code_powershell", lambda command: code_runner.run_powershell(command))

        # WhatsApp and Contact Automations
        def _send_wa(recipient, message):
            from jarvis.tools.productivity.whatsapp_client import whatsapp_client
            return whatsapp_client.send_message(recipient, message)
        self.register_tool("send_whatsapp_message", _send_wa)

        def _call_wa(recipient):
            from jarvis.tools.productivity.whatsapp_client import whatsapp_client
            return whatsapp_client.initiate_call(recipient)
        self.register_tool("whatsapp_call", _call_wa)

        self.register_tool("add_contact", lambda name, phone: semantic_store.add_contact(name, phone))
        self.register_tool("list_contacts", lambda: semantic_store.list_contacts())

        # Screenshot & Screen Capture
        def _take_screenshot(open_after=True):
            from jarvis.vision.screen_capture import screen_capture
            return screen_capture.capture_full_screen(open_after=open_after)
        self.register_tool("take_screenshot", _take_screenshot)

        # YouTube Playback
        def _play_yt(query="", media_type="video"):
            import re
            import urllib.parse
            import webbrowser

            clean_q = (query or "").strip()
            # If user explicitly asked for reels/shorts
            if media_type == "reels" or clean_q.lower() in ("reel", "reels", "shorts", "short"):
                target_url = "https://www.youtube.com/shorts"
                logger.info("Opening YouTube Shorts / Reels in foreground browser tab.")
                try:
                    webbrowser.open_new_tab(target_url)
                    return {"status": "success", "query": "reels", "url": target_url, "feedback": "Opening YouTube Reels, Sir."}
                except Exception as exc:
                    return {"status": "error", "error": str(exc), "feedback": f"Failed to open reels: {exc}"}

            if not clean_q or clean_q.lower() in ("youtube", "open youtube"):
                target_url = "https://www.youtube.com"
                try:
                    webbrowser.open_new_tab(target_url)
                    return {"status": "success", "query": "YouTube", "url": target_url, "feedback": "Opening YouTube, Sir."}
                except Exception as exc:
                    return {"status": "error", "error": str(exc), "feedback": f"Failed to open YouTube: {exc}"}

            # Clean query for songs / movies
            clean_q = re.sub(r"^(?:a\s+|some\s+)?(?:song|music|track|songs)\s*", "", clean_q, flags=re.IGNORECASE).strip() or clean_q
            if clean_q.lower() in ("song", "music", "a song", "some song", "track", "songs"):
                clean_q = "top trending hit music"

            logger.info(f"Opening YouTube playback for '{clean_q}' in foreground browser.")
            encoded_query = urllib.parse.quote(clean_q)
            fallback_url = f"https://www.youtube.com/results?search_query={encoded_query}"

            try:
                import pywhatkit
                pywhatkit.playonyt(clean_q)
                return {
                    "status": "success",
                    "query": clean_q,
                    "url": fallback_url,
                    "feedback": f"Playing '{clean_q}' on YouTube, Sir.",
                }
            except Exception as exc:
                logger.warning(f"pywhatkit.playonyt failed ({exc}); falling back to browser tab.")
                try:
                    webbrowser.open_new_tab(fallback_url)
                    return {
                        "status": "success",
                        "query": clean_q,
                        "url": fallback_url,
                        "feedback": f"Searching and playing '{clean_q}' on YouTube, Sir.",
                    }
                except Exception as open_err:
                    logger.error(f"Failed to open YouTube browser tab: {open_err}")
                    return {
                        "status": "error",
                        "error": str(open_err),
                        "feedback": f"Failed to open YouTube: {open_err}",
                    }
        self.register_tool("play_youtube", _play_yt)

        def _search_google(query):
            import os
            import urllib.parse
            import webbrowser
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            try:
                os.startfile(url)
            except Exception:
                webbrowser.open(url)
            return {"status": "success", "url": url}
        self.register_tool("search_google", _search_google)

        # Calendar & Reminders
        def _sched_reminder(title, time_expression):
            from jarvis.tools.productivity.calendar_manager import calendar_manager
            return calendar_manager.schedule_reminder(title, time_expression)
        self.register_tool("schedule_reminder", _sched_reminder)

        # Geolocation & Physical Location
        def _get_location():
            import json
            import urllib.request
            try:
                req = urllib.request.Request("http://ip-api.com/json/", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("status") == "success":
                        loc_str = f"{data.get('city')}, {data.get('regionName')}, {data.get('country')} (Lat: {data.get('lat')}, Lon: {data.get('lon')})"
                        return {"status": "success", "location": loc_str, "isp": data.get("isp")}
            except Exception:
                pass
            import time
            return {"status": "success", "location": f"Estimated Region (System Timezone: {time.tzname[0]})"}
        self.register_tool("get_current_location", _get_location)

        def _toggle_voice(enable=True):
            from jarvis.voice.listener import voice_listener
            voice_listener.start() if enable else voice_listener.stop()
        self.register_tool("toggle_voice", _toggle_voice)

        # Web Search, Wikipedia & Weather
        def _get_weather(location="London"):
            from jarvis.tools.web.search_engine import web_search
            return web_search.get_weather(location)
        self.register_tool("get_weather", _get_weather)

        def _search_wiki(query, sentences=3):
            from jarvis.tools.web.search_engine import web_search
            return web_search.search_wikipedia(query, sentences)
        self.register_tool("search_wikipedia", _search_wiki)

        def _search_ddg(query, max_results=5):
            from jarvis.tools.web.search_engine import web_search
            return web_search.search_duckduckgo(query, max_results)
        self.register_tool("search_duckduckgo", _search_ddg)

        # File Management & Directory Organization
        def _search_files(directory=".", pattern="*", max_results=50, recursive=True):
            from jarvis.tools.file_manager.file_ops import file_manager
            return file_manager.search_files(directory, pattern, max_results, recursive)
        self.register_tool("search_files", _search_files)

        def _read_file(file_path, max_lines=500):
            from jarvis.tools.file_manager.file_ops import file_manager
            return file_manager.read_file_content(file_path, max_lines)
        self.register_tool("read_file", _read_file)

        def _write_file(file_path, content, append=False):
            from jarvis.tools.file_manager.file_ops import file_manager
            return file_manager.write_file_content(file_path, content, append)
        self.register_tool("write_file", _write_file)

        def _organize_dir(directory):
            from jarvis.tools.file_manager.file_ops import file_manager
            return file_manager.organize_directory(directory)
        self.register_tool("organize_directory", _organize_dir)

        # Clipboard Management
        def _get_clipboard():
            from jarvis.tools.clipboard.clipboard_manager import clipboard_manager
            return clipboard_manager.get_clipboard()
        self.register_tool("get_clipboard", _get_clipboard)

        def _set_clipboard(text):
            from jarvis.tools.clipboard.clipboard_manager import clipboard_manager
            return clipboard_manager.set_clipboard(text)
        self.register_tool("set_clipboard", _set_clipboard)

        # Git Assistant
        def _get_git_status(repo_dir="."):
            from jarvis.tools.developer.git_assistant import git_assistant
            return git_assistant.get_status(repo_dir)
        self.register_tool("get_git_status", _get_git_status)

        def _get_git_commits(repo_dir=".", count=5):
            from jarvis.tools.developer.git_assistant import git_assistant
            return git_assistant.get_recent_commits(repo_dir, count)
        self.register_tool("get_git_recent_commits", _get_git_commits)

        # Workflow Automation
        def _run_wf(workflow_id):
            from jarvis.workflow.workflow_engine import workflow_engine
            return workflow_engine.execute_workflow(workflow_id)
        self.register_tool("run_workflow", _run_wf)

        # Email Notification
        def _send_email(to_address, subject, body, is_html=False):
            from jarvis.tools.productivity.email_client import email_client
            return email_client.send_email(to_address, subject, body, is_html)
        self.register_tool("send_email", _send_email)

        # Screen Vision & OCR
        def _analyze_vision():
            from jarvis.vision.vision_analyzer import vision_analyzer
            return vision_analyzer.analyze_screen()
        self.register_tool("analyze_screen_vision", _analyze_vision)

        # Browser Navigation
        def _open_url(url, new_window=False):
            from jarvis.tools.browser.browser_controller import browser_controller
            return browser_controller.open_url(url, new_window)
        self.register_tool("open_url", _open_url)

    def register_tool(self, name: str, func: Callable[..., Any]) -> None:
        """Register or override an executable tool."""
        self._tools[name] = func
        logger.debug(f"Registered tool: '{name}'")

    def get_preferred_provider(self) -> BaseLLMProvider:
        """Determine the active LLM backend based on configuration and availability."""
        preferred = self.settings.DEFAULT_LLM_PROVIDER.lower()

        if preferred == "gemini" and self.gemini_provider.is_available():
            return self.gemini_provider
        elif preferred == "openai" and self.openai_provider.is_available():
            return self.openai_provider

        # Fallback order
        if self.gemini_provider.is_available():
            return self.gemini_provider
        if self.openai_provider.is_available():
            return self.openai_provider

        return self.offline_provider

    def process_query(
        self,
        query: str,
        conversation_id: str = "default_session",
    ) -> Dict[str, Any]:
        """Process user input query through reasoning, execute any actions, and persist history."""
        import time
        import re

        logger.info(f"Processing query: '{query}' [Session: {conversation_id}]")

        # 0. Deduplication to prevent double execution if multiple inputs hear speech simultaneously
        now = time.time()
        dedup_key = re.sub(r"[^\w\s]", "", query.strip().lower())
        for k, (t, cached_res) in list(self._query_cache.items()):
            if now - t > 8.0:
                del self._query_cache[k]
        if dedup_key in self._query_cache:
            prev_t, prev_res = self._query_cache[dedup_key]
            if (now - prev_t) < 5.0:
                logger.info(f"Deduplicated repeated query within 5s: '{query}'")
                return prev_res

        # Notify event bus
        event_bus.publish_sync(
            Event(
                event_type=EventType.USER_QUERY_RECEIVED,
                payload={"query": query, "session_id": conversation_id},
            )
        )

        # 1. Fetch conversation history for multi-turn context
        history = conversation_store.get_recent_messages(conversation_id, limit=6)
        system_prompt = build_system_prompt()

        # Fast-Path: Evaluate deterministic desktop automations first (0.001s response time)
        offline_candidate = self.offline_provider.generate(
            prompt=query,
            system_prompt=system_prompt,
            conversation_history=history,
        )

        INSTANT_ACTIONS = {
            "launch_app", "close_window", "minimize_window", "maximize_window",
            "volume_up", "volume_down", "toggle_mute", "media_play_pause", "media_next", "media_previous", "refresh_page",
            "get_battery_status", "get_memory_status", "get_disk_usage", "get_system_summary",
            "lock_workstation", "create_note", "schedule_reminder",
            "play_youtube", "search_wikipedia", "search_google", "get_weather",
            "send_whatsapp_message", "whatsapp_call", "add_contact", "list_contacts",
            "take_screenshot", "get_clipboard", "set_clipboard", "run_code_powershell",
            "organize_directory", "get_current_location"
        }

        provider = self.offline_provider
        response: Optional[LLMResponse] = None

        # If offline engine matched a direct desktop action, execute directly without cloud latency
        if offline_candidate.tool_calls and any(tc.name in INSTANT_ACTIONS for tc in offline_candidate.tool_calls):
            response = offline_candidate
        elif offline_candidate.content and not offline_candidate.content.startswith("At your service, Sir. Ready to execute your command") and not offline_candidate.tool_calls:
            # Matches instant math, time, date, greetings
            response = offline_candidate
        else:
            # Route to Generative AI (Gemini) for knowledge, coding, and open-ended conversation
            active_llm = self.get_preferred_provider()
            try:
                response = active_llm.generate(
                    prompt=query,
                    system_prompt=system_prompt,
                    conversation_history=history,
                )
                provider = active_llm
            except Exception as exc:
                logger.warning(f"Active provider '{active_llm.__class__.__name__}' failed: {exc}. Falling back to OfflineProvider.")
                response = offline_candidate

        executed_actions: List[Dict[str, Any]] = []

        # 2. Execute any requested tool calls
        if response.tool_calls:
            for tc in response.tool_calls:
                action_name = tc.name
                handler = self._tools.get(action_name)
                if handler:
                    logger.info(f"Executing tool '{action_name}' with args: {tc.arguments}")
                    event_bus.publish_sync(
                        Event(
                            event_type=EventType.TOOL_EXECUTION_REQUESTED,
                            payload={"action": action_name, "arguments": tc.arguments},
                        )
                    )
                    try:
                        result = handler(**tc.arguments) if tc.arguments else handler()
                        
                        # Check if tool returned an error dictionary
                        if isinstance(result, dict) and (result.get("status") == "error" or result.get("success") is False):
                            err_msg = result.get("error") or result.get("feedback") or f"Action {action_name} failed"
                            response.content = result.get("feedback") or f"Error executing {action_name}: {err_msg}"
                            executed_actions.append({
                                "action": action_name,
                                "arguments": tc.arguments,
                                "status": "error",
                                "error": str(err_msg),
                                "result": str(result),
                            })
                            event_bus.publish_sync(
                                Event(
                                    event_type=EventType.TOOL_EXECUTION_FAILED,
                                    payload={"action": action_name, "error": str(err_msg)},
                                )
                            )
                        else:
                            # Success handlers
                            if action_name == "take_screenshot" and isinstance(result, dict):
                                response.content = result.get("feedback") or result.get("message") or "Screenshot saved successfully, Sir."
                            elif action_name == "get_current_location" and isinstance(result, dict) and "location" in result:
                                response.content = f"Your current detected location is: {result['location']}, Sir."
                            elif action_name == "get_battery_status" and result is not None:
                                status_str = result.status_text if hasattr(result, "status_text") else str(result)
                                response.content = f"Your laptop battery is currently at {status_str}, Sir."
                            elif action_name == "get_memory_status" and result is not None:
                                response.content = f"System RAM usage is {result.used_gb} GB out of {result.total_gb} GB ({result.load_percent}%), Sir."
                            elif action_name in ("send_whatsapp_message", "whatsapp_call") and isinstance(result, dict) and "feedback" in result:
                                response.content = result["feedback"]
                            elif action_name == "play_youtube" and isinstance(result, dict):
                                response.content = result.get("feedback") or f"Playing '{result.get('query')}' on YouTube, Sir."
                            elif action_name == "get_weather" and isinstance(result, dict):
                                response.content = result.get("summary", f"Weather report: {result}")
                            elif action_name == "search_wikipedia" and isinstance(result, dict):
                                if result.get("success"):
                                    response.content = f"According to Wikipedia for {result.get('title')}: {result.get('summary')}"
                                else:
                                    response.content = f"I could not retrieve Wikipedia info for '{result.get('query')}': {result.get('error')}"
                            elif action_name == "search_duckduckgo" and isinstance(result, list):
                                if result:
                                    top_item = result[0]
                                    snippet = top_item.get("snippet") or top_item.get("title")
                                    response.content = f"{snippet}"
                                else:
                                    from jarvis.tools.web.search_engine import web_search
                                    q = tc.arguments.get("query", "")
                                    wiki = web_search.search_wikipedia(q)
                                    if wiki.get("success"):
                                        response.content = f"According to Wikipedia for {wiki.get('title')}: {wiki.get('summary')}"
                                    else:
                                        response.content = f"I could not find an encyclopedic answer for '{q}', Sir."
                            elif action_name == "organize_directory" and isinstance(result, dict):
                                if result.get("success"):
                                    response.content = f"Organized files in '{result.get('directory')}'. Summary: {result.get('summary')}, Sir."
                                else:
                                    response.content = f"Failed to organize directory: {result.get('error')}"
                            elif action_name == "get_git_status" and isinstance(result, dict):
                                st = result.get("status_text") or "Clean working tree, nothing to commit."
                                response.content = f"Git status:\n{st}"
                            elif action_name == "run_workflow" and isinstance(result, dict):
                                wf_name = result.get("workflow_name", "Routine")
                                dur = result.get("duration_ms", 0)
                                response.content = f"Workflow '{wf_name}' completed in {dur:.1f}ms, Sir."
                            elif action_name == "get_clipboard":
                                response.content = f"Current clipboard content: \"{result}\", Sir."
                            elif action_name == "set_clipboard":
                                response.content = "Successfully copied text to your clipboard, Sir."

                            executed_actions.append({
                                "action": action_name,
                                "arguments": tc.arguments,
                                "status": "success",
                                "result": str(result),
                            })
                            event_bus.publish_sync(
                                Event(
                                    event_type=EventType.TOOL_EXECUTION_COMPLETED,
                                    payload={"action": action_name, "result": str(result)},
                                )
                            )
                    except Exception as err:
                        logger.error(f"Error executing tool '{action_name}': {err}")
                        err_str = str(err)
                        response.content = f"Error executing {action_name}: {err_str}"
                        executed_actions.append({
                            "action": action_name,
                            "arguments": tc.arguments,
                            "status": "error",
                            "error": err_str,
                        })
                        event_bus.publish_sync(
                            Event(
                                event_type=EventType.TOOL_EXECUTION_FAILED,
                                payload={"action": action_name, "error": err_str},
                            )
                        )
                else:
                    logger.warning(f"Requested tool '{action_name}' not found in registry.")

        # 3. Persist messages in conversation store
        conversation_store.add_message(conversation_id, role="user", content=query)
        conversation_store.add_message(
            conversation_id,
            role="assistant",
            content=response.content,
            tool_calls=[{"name": tc.name, "args": tc.arguments} for tc in response.tool_calls] if response.tool_calls else None,
        )

        # Notify event bus
        event_bus.publish_sync(
            Event(
                event_type=EventType.AI_RESPONSE_GENERATED,
                payload={"response": response.content, "session_id": conversation_id},
            )
        )

        final_result = {
            "query": query,
            "response": response.content,
            "provider_used": provider.__class__.__name__,
            "actions_executed": executed_actions,
            "session_id": conversation_id,
        }
        self._query_cache[dedup_key] = (now, final_result)
        return final_result


# Singleton action router instance
action_router = ActionRouter()
