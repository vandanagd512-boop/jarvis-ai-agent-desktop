"""Deterministic offline reasoning engine and real-world intent classifier."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from jarvis.brain.llm_provider import BaseLLMProvider, LLMResponse, ToolCall
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.OfflineBrain")


class OfflineProvider(BaseLLMProvider):
    """Zero-dependency, production deterministic reasoning engine.

    Parses natural language commands for real-world Windows desktop actions:
    WhatsApp messaging/calling, Instagram/web opening, screenshots, media control,
    system monitoring, notes, reminders, YouTube playback, and encyclopedic knowledge.
    """

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Parse natural language command and map to real desktop automation tools."""
        clean_prompt = prompt.strip()

        # Clean leading wake-words and courteous prefixes
        clean_prompt = re.sub(r"^(?:hey\s+|hi\s+|ok\s+|hello\s+)?jarvis[,:\s]*", "", clean_prompt, flags=re.IGNORECASE).strip()
        clean_prompt = re.sub(r"^(?:please\s+|can\s+you\s+|could\s+you\s+|would\s+you\s+)", "", clean_prompt, flags=re.IGNORECASE).strip()
        if not clean_prompt:
            clean_prompt = prompt.strip()

        text = clean_prompt.lower()
        tool_calls: List[ToolCall] = []

        # 1. Shell commands or Python executions
        if text.startswith("python ") or text.startswith("python.exe ") or text.startswith("py "):
            if "run_tests" in text:
                return LLMResponse(
                    content="Executing test suite now.",
                    tool_calls=[ToolCall(name="run_code_powershell", arguments={"command": prompt})],
                )
            if "--mode voice" in text or "voice" in text:
                return LLMResponse(
                    content="Voice listener enabled.",
                    tool_calls=[ToolCall(name="toggle_voice", arguments={"enable": True})],
                )
            return LLMResponse(
                content=f"Running command: '{prompt}'",
                tool_calls=[ToolCall(name="run_code_powershell", arguments={"command": prompt})],
            )

        if text.startswith("powershell ") or text.startswith("cmd ") or any(text.startswith(c) for c in ["dir", "ipconfig", "ping ", "git "]):
            return LLMResponse(
                content=f"Executing system command: '{prompt}'",
                tool_calls=[ToolCall(name="run_code_powershell", arguments={"command": prompt})],
            )

        # 2. Screenshot & Screen Capture
        if any(w in text for w in ["screenshot", "take a screenshot", "capture screen", "screen capture", "take screenshot"]):
            tool_calls.append(ToolCall(name="take_screenshot", arguments={"open_after": True}))
            return LLMResponse(
                content="Capturing screenshot now, Sir.",
                tool_calls=tool_calls,
            )

        # 3. Calling Someone (WhatsApp / Phone Call)
        # Matches: "call [name] on whatsapp", "call alex on whatsapp", "call to alex", "call someone", "whatsapp call alex", "call on whatsapp alex"
        call_match = re.search(
            r"^(?:(?:open\s+whatsapp\s+(?:and\s+)?)?(?:call\s+to|call|make\s+a\s+call\s+to|phone\s+call\s+to|whatsapp\s+call|call\s+on\s+whatsapp|dial)\s+([a-zA-Z0-9_\+\s]+?)(?:\s+on\s+whatsapp|\s+on\s+phone)?)$",
            text,
            re.IGNORECASE,
        )
        if call_match:
            raw_rec = call_match.group(1).replace("on whatsapp", "").replace("on phone", "").strip()
            recipient = re.sub(r"^to\s+", "", raw_rec).strip()
            tool_calls.append(ToolCall(name="whatsapp_call", arguments={"recipient": recipient}))
            return LLMResponse(
                content=f"Initiating call with {recipient.title()}, Sir.",
                tool_calls=tool_calls,
            )

        # 4. WhatsApp Messaging
        wa_text_match = re.search(
            r"(?:(?:open whatsapp\s+(?:and\s+)?)?(?:chat with|chat|text|message|send message to|send whatsapp(?: message)? to|whatsapp)\s+([a-zA-Z0-9_\+]+)(?:\s+on whatsapp)?(?:\s*:\s*|\s+saying\s+|\s+that\s+|\s+)(.+))",
            text,
            re.IGNORECASE,
        )
        if wa_text_match:
            recipient = wa_text_match.group(1).replace("on whatsapp", "").strip()
            msg = wa_text_match.group(2).strip()
            tool_calls.append(ToolCall(name="send_whatsapp_message", arguments={"recipient": recipient, "message": msg}))
            return LLMResponse(
                content=f"Sending WhatsApp message to {recipient.title()}: \"{msg}\"",
                tool_calls=tool_calls,
            )

        wa_open_msg_match = re.search(
            r"(?:(?:open whatsapp\s+(?:and\s+)?)?(?:chat with|chat|text|message|to\s+message)\s+([a-zA-Z0-9_\+]+))$",
            text,
            re.IGNORECASE,
        )
        if wa_open_msg_match:
            recipient = wa_open_msg_match.group(1).strip()
            tool_calls.append(ToolCall(name="send_whatsapp_message", arguments={"recipient": recipient, "message": ""}))
            return LLMResponse(
                content=f"Opening WhatsApp chat with {recipient.title()}, Sir.",
                tool_calls=tool_calls,
            )

        # 5. Contacts Management
        save_contact_match = re.search(r"(?:save|add)\s+contact\s+([a-zA-Z0-9_ ]+?)\s*:\s*([0-9\+\-\(\) ]+)", text)
        if save_contact_match:
            c_name = save_contact_match.group(1).strip()
            c_phone = save_contact_match.group(2).strip()
            tool_calls.append(ToolCall(name="add_contact", arguments={"name": c_name, "phone": c_phone}))
            return LLMResponse(content=f"Saved contact '{c_name.title()}' with phone: {c_phone}.", tool_calls=tool_calls)

        if "list contacts" in text or "show contacts" in text:
            tool_calls.append(ToolCall(name="list_contacts", arguments={}))
            return LLMResponse(content="Retrieving your contacts directory, Sir.", tool_calls=tool_calls)

        # 6. Wikipedia Encyclopedic Lookups (Checked before hardware queries to avoid substring collision)
        wiki_match = re.search(r"(?:search\s+wikipedia\s+(?:for\s+)?|wikipedia\s+(?:for\s+)?|wiki\s+)(.+)", clean_prompt, re.IGNORECASE)
        if wiki_match:
            wiki_topic = wiki_match.group(1).strip()
            tool_calls.append(ToolCall(name="search_wikipedia", arguments={"query": wiki_topic}))
            return LLMResponse(content=f"Searching Wikipedia for '{wiki_topic}', Sir.", tool_calls=tool_calls)

        # 7. Geolocation & Current Physical Location
        if any(w in text for w in [
            "where am i", "exact place of me", "my location", "what is my location", 
            "where do i live", "current place", "my current city", "my city", "exact place"
        ]):
            tool_calls.append(ToolCall(name="get_current_location", arguments={}))
            return LLMResponse(
                content="Detecting your current physical location and geographic coordinates, Sir.",
                tool_calls=tool_calls,
            )

        # 8. Reels / Shorts Playback
        if any(w in text for w in ["play reel", "play reels", "watch reel", "watch reels", "open reel", "open reels", "play shorts", "watch shorts"]):
            tool_calls.append(ToolCall(name="play_youtube", arguments={"query": "reels", "media_type": "reels"}))
            return LLMResponse(content="Opening Reels and Shorts for you, Sir.", tool_calls=tool_calls)

        # 8b. Movie Playback
        movie_match = re.search(r"^(?:open\s+youtube\s+(?:and\s+)?)?(?:play|watch|search)\s+(?:a\s+)?movie\s*(.*)$", text, re.IGNORECASE)
        if movie_match:
            movie_title = movie_match.group(1).replace("on youtube", "").strip()
            if not movie_title or movie_title.lower() in ("some movie", "a movie", "movies", "the movie"):
                clean_movie = "trending full movies trailers"
            else:
                clean_movie = f"{movie_title} full movie"
            tool_calls.append(ToolCall(name="play_youtube", arguments={"query": clean_movie, "media_type": "movie"}))
            return LLMResponse(content=f"Searching and playing '{clean_movie}' on YouTube, Sir.", tool_calls=tool_calls)

        # 8c. YouTube & Music / Song Playback
        # Matches: "play [x] on youtube", "play [x]", "open youtube play some song", "youtube [x]"
        direct_yt = re.search(r"^(?:open\s+youtube\s+(?:and\s+)?)?(?:play|listen\s+to|search(?:\s+for)?)\s+(?:on\s+youtube\s+)?(.+?)(?:\s+on\s+youtube)?$|^youtube\s+(.+)$", text, re.IGNORECASE)
        if direct_yt and ("youtube" in text or text.startswith("play ") or text.startswith("listen ") or text.startswith("search ")):
            raw_q = (direct_yt.group(1) or direct_yt.group(2) or "").strip()
            clean_q = re.sub(r"^(?:a\s+|some\s+)?(?:song|music|track|songs)\s*", "", raw_q, flags=re.IGNORECASE).strip()
            clean_q = clean_q or raw_q
            if not clean_q or clean_q.lower() in ("song", "music", "a song", "track", "songs", "some song", "some songs"):
                clean_q = "top trending hit music"

            tool_calls.append(ToolCall(name="play_youtube", arguments={"query": clean_q, "media_type": "song"}))
            return LLMResponse(content=f"Searching and playing '{clean_q}' on YouTube for you, Sir.", tool_calls=tool_calls)

        if text in ["open youtube", "launch youtube", "start youtube", "youtube"]:
            tool_calls.append(ToolCall(name="play_youtube", arguments={"query": "youtube"}))
            return LLMResponse(content="Opening YouTube, Sir.", tool_calls=tool_calls)

        # 9. Web Search (Google)
        google_match = re.search(r"(?:search google for|google|search web for)\s+(.+)", text)
        if google_match:
            query = google_match.group(1).strip()
            tool_calls.append(ToolCall(name="search_google", arguments={"query": query}))
            return LLMResponse(content=f"Searching Google for: '{query}'.", tool_calls=tool_calls)

        # 10. Multi-Step Automated Workflows & Routines
        if any(w in text for w in ["morning briefing", "run morning briefing", "daily briefing"]):
            tool_calls.append(ToolCall(name="run_workflow", arguments={"workflow_id": "morning_briefing"}))
            return LLMResponse(content="Executing Morning System Briefing workflow routine, Sir.", tool_calls=tool_calls)

        if any(w in text for w in ["focus mode", "start focus mode", "focus work mode"]):
            tool_calls.append(ToolCall(name="run_workflow", arguments={"workflow_id": "focus_mode"}))
            return LLMResponse(content="Initiating Focus Work Mode workflow routine, Sir.", tool_calls=tool_calls)

        wf_match = re.search(r"^(?:run|execute|start)(?:\s+workflow|\s+routine)\s+([a-zA-Z0-9_-]+)$", text)
        if wf_match:
            wf_id = wf_match.group(1).strip()
            tool_calls.append(ToolCall(name="run_workflow", arguments={"workflow_id": wf_id}))
            return LLMResponse(content=f"Executing workflow routine '{wf_id}', Sir.", tool_calls=tool_calls)

        # 11. Application & Web Platform Launching
        open_match = re.search(r"^(?:open|launch|start|run)\s+([a-zA-Z0-9_\-\. ]+)$", text)
        if open_match:
            app_name = open_match.group(1).strip()
            tool_calls.append(ToolCall(name="launch_app", arguments={"target": app_name}))
            return LLMResponse(
                content=f"Opening {app_name.title()} right away, Sir.",
                tool_calls=tool_calls,
            )

        # 12. Windows Management & Controls
        if "close window" in text or "close" in text:
            target_match = re.search(r"close\s+([a-zA-Z0-9_\- ]+)", text)
            target = target_match.group(1).replace("window", "").strip() if target_match else ""
            tool_calls.append(ToolCall(name="close_window", arguments={"title_query": target}))
            return LLMResponse(content=f"Closing {target or 'active'} window.", tool_calls=tool_calls)

        if "minimize" in text:
            target_match = re.search(r"minimize\s+([a-zA-Z0-9_\- ]+)", text)
            target = target_match.group(1).replace("window", "").strip() if target_match else ""
            tool_calls.append(ToolCall(name="minimize_window", arguments={"title_query": target}))
            return LLMResponse(content=f"Minimizing {target or 'current'} window.", tool_calls=tool_calls)

        if "maximize" in text:
            target_match = re.search(r"maximize\s+([a-zA-Z0-9_\- ]+)", text)
            target = target_match.group(1).replace("window", "").strip() if target_match else ""
            tool_calls.append(ToolCall(name="maximize_window", arguments={"title_query": target}))
            return LLMResponse(content=f"Maximizing {target or 'current'} window.", tool_calls=tool_calls)

        # 13. Hardware Volume & Media
        if re.search(r"\b(?:volume\s+up|increase\s+volume|turn\s+up\s+sound|louder|higher\s+volume)\b", text):
            tool_calls.append(ToolCall(name="volume_up", arguments={"steps": 3}))
            return LLMResponse(content="Increasing volume, Sir.", tool_calls=tool_calls)

        if re.search(r"\b(?:volume\s+down|decrease\s+volume|lower\s+sound|turn\s+down\s+sound|quieter)\b", text):
            tool_calls.append(ToolCall(name="volume_down", arguments={"steps": 3}))
            return LLMResponse(content="Lowering volume, Sir.", tool_calls=tool_calls)

        # Volume Mute / Volume Off (covers "volume of", "volume off", "sound off", "mute")
        if re.search(r"\b(?:volume\s+(?:off|of|zero)|mute|unmute|sound\s+off|turn\s+off\s+sound|turn\s+off\s+audio|mute\s+audio|silence)\b", text):
            tool_calls.append(ToolCall(name="toggle_mute", arguments={}))
            return LLMResponse(content="Muting system audio, Sir.", tool_calls=tool_calls)

        if any(w in text for w in ["refresh", "reload", "refresh page", "refresh that page", "reload page", "reload that page", "refresh the page"]):
            tool_calls.append(ToolCall(name="refresh_page", arguments={}))
            return LLMResponse(content="Refreshing page, Sir.", tool_calls=tool_calls)

        if any(w in text for w in [
            "next play", "play next", "next song", "next track", "next video", "skip song", "skip track", "skip video"
        ]) or text in ["next", "skip", "play next song"]:
            tool_calls.append(ToolCall(name="media_next", arguments={}))
            return LLMResponse(content="Skipping to next track, Sir.", tool_calls=tool_calls)

        if any(w in text for w in [
            "previous song", "previous track", "previous video", "prev song", "prev track"
        ]) or text in ["previous", "prev", "go back"]:
            tool_calls.append(ToolCall(name="media_previous", arguments={}))
            return LLMResponse(content="Playing previous track, Sir.", tool_calls=tool_calls)

        if text in [
            "play", "pause", "resume", "pause music", "stop music", "resume music",
            "toggle playback", "pause video", "resume video", "pause it", "play it"
        ]:
            tool_calls.append(ToolCall(name="media_play_pause", arguments={}))
            return LLMResponse(content="Toggling media playback, Sir.", tool_calls=tool_calls)

        # 14. System Metrics & Battery / Charge Status (using strict word boundaries to avoid collision with words like 'program')
        if re.search(r"\b(?:battery|charging|battery\s+level|charge\s+percent|battery\s+percentage|laptop\s+battery|power\s+status|laptop\s+charge|how\s+much\s+charge)\b", text):
            tool_calls.append(ToolCall(name="get_battery_status", arguments={}))
            return LLMResponse(
                content="Checking battery charge percentage, Sir.",
                tool_calls=tool_calls,
            )

        if re.search(r"\b(?:ram|memory\s+usage|memory\s+status|ram\s+usage|ram\s+memory|system\s+ram)\b", text):
            tool_calls.append(ToolCall(name="get_memory_status", arguments={}))
            return LLMResponse(
                content="Querying system memory metrics.",
                tool_calls=tool_calls,
            )

        if re.search(r"\b(?:disk\s+space|disk\s+usage|hard\s+drive|c:\s*drive|storage\s+usage|free\s+space)\b", text) or text in ["disk", "storage"]:
            tool_calls.append(ToolCall(name="get_disk_usage", arguments={"drive": "C:"}))
            return LLMResponse(
                content="Analyzing C: drive disk capacity.",
                tool_calls=tool_calls,
            )

        if any(w in text for w in ["system status", "system health", "hardware status", "system summary"]):
            tool_calls.append(ToolCall(name="get_system_summary", arguments={}))
            return LLMResponse(
                content="Generating full system telemetry report.",
                tool_calls=tool_calls,
            )

        # 15. Workstation Lock
        if "lock pc" in text or "lock computer" in text or "lock workstation" in text or "lock screen" in text:
            tool_calls.append(ToolCall(name="lock_workstation", arguments={}))
            return LLMResponse(content="Locking your workstation immediately, Sir.", tool_calls=tool_calls)

        # 16. Notes & Reminders
        note_match = re.search(r"(?:take\s+a\s+note|add\s+note|new\s+note|write\s+note)(?::|\s+that|\s+to)?\s+(.+)", text)
        if note_match:
            content = note_match.group(1).strip()
            tool_calls.append(ToolCall(name="create_note", arguments={"title": "Quick Note", "content": content}))
            return LLMResponse(content=f"Saved note: '{content}'", tool_calls=tool_calls)

        rem_match = re.search(r"remind\s+me\s+(?:to\s+)?(.+?)\s+(in\s+\d+\s*(?:minutes|hours|days)|tomorrow.*)", text)
        if rem_match:
            title = rem_match.group(1).strip()
            time_expr = rem_match.group(2).strip()
            tool_calls.append(ToolCall(name="schedule_reminder", arguments={"title": title, "time_expression": time_expr}))
            return LLMResponse(content=f"Scheduled reminder: '{title}' ({time_expr}).", tool_calls=tool_calls)

        # 17. Weather & Meteorological Forecasts
        weather_match = re.search(r"(?:(?:what(?:'s| is) the )?weather(?: forecast)?\s+(?:in|for)\s+([a-zA-Z\s]+)|weather\s+in\s+([a-zA-Z\s]+)|^weather$)", text)
        if weather_match:
            loc = (weather_match.group(1) or weather_match.group(2) or "London").strip().title()
            tool_calls.append(ToolCall(name="get_weather", arguments={"location": loc}))
            return LLMResponse(content=f"Checking real-time weather forecast for {loc}, Sir.", tool_calls=tool_calls)

        # 18. File Organization
        if any(w in text for w in ["organize downloads", "clean downloads", "clean up downloads"]):
            import os
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            tool_calls.append(ToolCall(name="organize_directory", arguments={"directory": downloads_dir}))
            return LLMResponse(content="Organizing files in your Downloads folder into categories, Sir.", tool_calls=tool_calls)

        if any(w in text for w in ["organize desktop", "clean desktop"]):
            import os
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            tool_calls.append(ToolCall(name="organize_directory", arguments={"directory": desktop_dir}))
            return LLMResponse(content="Organizing files on your Desktop into categories, Sir.", tool_calls=tool_calls)

        # 19. Git Developer Assistant
        if "git status" in text or "check git status" in text:
            tool_calls.append(ToolCall(name="get_git_status", arguments={"repo_dir": "."}))
            return LLMResponse(content="Checking Git repository status, Sir.", tool_calls=tool_calls)

        if any(w in text for w in ["git log", "git commits", "recent commits"]):
            tool_calls.append(ToolCall(name="get_git_recent_commits", arguments={"repo_dir": ".", "count": 5}))
            return LLMResponse(content="Retrieving recent Git commits, Sir.", tool_calls=tool_calls)

        # 20. Clipboard Operations
        if any(w in text for w in ["read clipboard", "what's on my clipboard", "what is on my clipboard", "show clipboard", "get clipboard"]):
            tool_calls.append(ToolCall(name="get_clipboard", arguments={}))
            return LLMResponse(content="Accessing clipboard content, Sir.", tool_calls=tool_calls)

        copy_match = re.search(r"^(?:copy\s+to\s+clipboard|copy\s+into\s+clipboard|clipboard\s+copy)\s+(.+)", text)
        if copy_match:
            clip_text = copy_match.group(1).strip()
            tool_calls.append(ToolCall(name="set_clipboard", arguments={"text": clip_text}))
            return LLMResponse(content=f"Copying \"{clip_text}\" to clipboard, Sir.", tool_calls=tool_calls)

        # 21. Screen Vision & OCR
        if any(w in text for w in ["analyze screen", "ocr screen", "read screen text", "screen vision"]):
            tool_calls.append(ToolCall(name="analyze_screen_vision", arguments={}))
            return LLMResponse(content="Analyzing current screen with multimodal vision and OCR, Sir.", tool_calls=tool_calls)

        # 22. Conversational Greetings & Identity
        if any(w in text for w in ["hello", "hey", "hi jarvis", "good morning", "good evening", "greetings"]):
            return LLMResponse(content="Greetings, Sir. JARVIS is online and ready for your commands.")

        if "who are you" in text or "what are you" in text:
            return LLMResponse(
                content="I am JARVIS, your personal Windows AI Desktop Assistant. I can control your desktop apps, open Instagram and WhatsApp, text or call contacts, take screenshots, manage media, track performance, and automate tasks."
            )

        if any(w in text for w in ["thank you", "thanks jarvis", "thanks"]):
            return LLMResponse(content="Always a pleasure to be of service, Sir.")

        # 23. Date & Current Time
        if re.search(r"\b(?:what(?:\s+is|\s+'s)?\s+(?:the\s+)?time|current\s+time|tell\s+(?:me\s+)?(?:the\s+)?time)\b", text):
            from datetime import datetime
            now_t = datetime.now().strftime("%I:%M %p")
            return LLMResponse(content=f"The current time is {now_t}, Sir.")

        if re.search(r"\b(?:what(?:\s+is|\s+'s)?\s+(?:the\s+)?(?:date|day)|today(?:\s+'s)?\s+date|what\s+day\s+is\s+(?:it\s+)?today)\b", text):
            from datetime import datetime
            now_d = datetime.now().strftime("%A, %B %d, %Y")
            return LLMResponse(content=f"Today is {now_d}, Sir.")

        # 24. Arithmetic Math Calculations (e.g., "what is 25 * 4", "calculate 100 / 5")
        calc_match = re.search(r"(?:calculate|what\s+is|what's)\s+([\d\.\s\+\-\*\/\(\)\%]+)$", text)
        if calc_match:
            expr = calc_match.group(1).strip()
            if any(op in expr for op in ["+", "-", "*", "/", "%"]):
                try:
                    allowed_chars = set("0123456789+-*/.() %")
                    if set(expr).issubset(allowed_chars):
                        res = eval(expr, {"__builtins__": {}}, {})
                        return LLMResponse(content=f"The result of {expr} is {res}, Sir.")
                except Exception:
                    pass

        # 25. General Out-of-the-Box Knowledge & Questions (e.g. "what is...", "who is...", "explain...")
        question_match = re.search(
            r"^(?:what\s+is|who\s+is|who\s+was|tell\s+me\s+about|explain|describe|can\s+you\s+explain|how\s+does|why\s+is)\s+([a-zA-Z0-9_\-\s]+?)(?:\?|$)",
            clean_prompt,
            re.IGNORECASE,
        )
        if question_match:
            topic = question_match.group(1).strip()
            tool_calls.append(ToolCall(name="search_duckduckgo", arguments={"query": topic}))
            return LLMResponse(
                content=f"Retrieving knowledge for '{topic}', Sir.",
                tool_calls=tool_calls,
            )

        # 26. General question fallback
        if "?" in prompt or any(text.startswith(q) for q in ["how", "why", "when", "which", "where", "what", "who"]):
            q_clean = re.sub(r"^(?:search\s+for|can\s+you\s+tell\s+me\s+about|tell\s+me\s+about)\s+", "", clean_prompt, flags=re.IGNORECASE).strip()
            tool_calls.append(ToolCall(name="search_duckduckgo", arguments={"query": q_clean}))
            return LLMResponse(
                content=f"Looking up '{q_clean}', Sir.",
                tool_calls=tool_calls,
            )

        # Default fallback
        return LLMResponse(
            content=f"At your service, Sir. Ready to execute your command: '{clean_prompt}'."
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ):
        """Yield response tokens sequentially."""
        res = self.generate(prompt, system_prompt, conversation_history)
        for token in res.content.split():
            yield token + " "
