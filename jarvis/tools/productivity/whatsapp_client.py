"""WhatsApp automation for text messaging and calling with contacts.json mapping and GUI shortcut automation."""

from __future__ import annotations
import json
import os
import re
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional
from jarvis.core.logger import get_logger
from jarvis.memory.semantic_store import semantic_store

logger = get_logger("JARVIS.WhatsApp")


def _get_contacts_file_path() -> Path:
    """Resolve location of contacts.json."""
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    data_contacts = base_dir / "data" / "contacts.json"
    root_contacts = base_dir / "contacts.json"
    if data_contacts.exists():
        return data_contacts
    if root_contacts.exists():
        return root_contacts
    # Default to data/contacts.json
    data_contacts.parent.mkdir(parents=True, exist_ok=True)
    return data_contacts


def load_contacts_map() -> Dict[str, str]:
    """Load spoken name -> phone number mapping from contacts.json."""
    contacts_path = _get_contacts_file_path()
    if contacts_path.exists():
        try:
            with open(contacts_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k).strip().lower(): str(v).strip() for k, v in data.items()}
        except Exception as exc:
            logger.error(f"Failed to load contacts.json from {contacts_path}: {exc}")
    return {}


class WhatsAppClient:
    """Automates sending WhatsApp text messages and initiating calls."""

    def resolve_recipient_number(self, recipient_or_name: str) -> Optional[Dict[str, str]]:
        """Resolve a spoken name (e.g. 'Alex', 'Mom') or raw phone number.

        Checks:
        1. contacts.json mapping (name -> international phone number with country code)
        2. SQLite semantic_store contacts
        3. Raw phone number string (with optional + and digits)
        Returns None if contact is missing.
        """
        target = recipient_or_name.strip()
        if not target:
            return None

        # 1. Check contacts.json map
        contacts_map = load_contacts_map()
        name_key = target.lower()
        if name_key in contacts_map:
            return {"name": target, "phone": contacts_map[name_key]}

        # 2. Check semantic_store SQLite database
        try:
            contact = semantic_store.get_contact_by_name(target)
            if contact and contact.get("phone"):
                return {"name": contact["name"], "phone": contact["phone"].strip()}
        except Exception as exc:
            logger.debug(f"Semantic store lookup error for '{target}': {exc}")

        # 3. Check if target is a raw phone number (e.g. '+1234567890' or '9876543210')
        digits_only = re.sub(r"[^\d]", "", target)
        if len(digits_only) >= 7:
            formatted_phone = target if target.startswith("+") else f"+{digits_only}"
            return {"name": target, "phone": formatted_phone}

        # Contact not found
        return None

    def send_message(self, recipient: str, message: str) -> Dict[str, Any]:
        """Open WhatsApp and send message to recipient."""
        resolved = self.resolve_recipient_number(recipient)
        if not resolved:
            error_msg = f"Contact {recipient} not found."
            logger.warning(error_msg)
            try:
                from jarvis.voice.tts import tts_engine
                tts_engine.speak(error_msg, wait=False)
            except Exception:
                pass
            return {
                "success": False,
                "status": "error",
                "error": error_msg,
                "feedback": error_msg,
            }

        phone_number = resolved["phone"]
        name = resolved["name"]
        clean_msg = message.strip() or "Hello!"
        encoded_text = urllib.parse.quote(clean_msg)

        logger.info(f"Opening WhatsApp chat for {name} ({phone_number})")
        # Launch chat via URI
        cmd = f'start "" "whatsapp://send?phone={phone_number}&text={encoded_text}"'
        try:
            os.system(cmd)
            channel = "desktop_app"
        except Exception as exc:
            logger.warning(f"os.system whatsapp:// failed ({exc}); falling back to web browser.")
            webbrowser.open(f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_text}")
            channel = "web_browser"

        feedback = f"WhatsApp opened for {name.title()} ({phone_number}) with message: \"{clean_msg}\"."
        return {
            "success": True,
            "status": "success",
            "recipient": name,
            "phone": phone_number,
            "message": clean_msg,
            "channel": channel,
            "feedback": feedback,
        }

    def initiate_call(self, recipient: str) -> Dict[str, Any]:
        """Initiate a WhatsApp voice/video call with recipient.

        Launches chat via whatsapp://send?phone={phone_number}, waits 2 seconds for focus,
        and triggers pyautogui.hotkey('ctrl', 'shift', 'c') to begin call.
        """
        resolved = self.resolve_recipient_number(recipient)
        if not resolved:
            error_msg = f"Contact {recipient} not found."
            logger.warning(error_msg)
            try:
                from jarvis.voice.tts import tts_engine
                tts_engine.speak(error_msg, wait=False)
            except Exception:
                pass
            return {
                "success": False,
                "status": "error",
                "error": error_msg,
                "feedback": error_msg,
            }

        phone_number = resolved["phone"]
        name = resolved["name"]
        logger.info(f"Initiating WhatsApp call with {name} ({phone_number})")

        # Launch chat via URI
        cmd = f'start "" "whatsapp://send?phone={phone_number}"'
        try:
            os.system(cmd)
            channel = "desktop_call"
        except Exception as exc:
            logger.warning(f"os.system whatsapp:// failed ({exc}); falling back to web browser.")
            webbrowser.open(f"https://web.whatsapp.com/send?phone={phone_number}")
            channel = "web_chat"

        # Wait 2 seconds for focus, then trigger pyautogui.hotkey('ctrl', 'shift', 'c')
        def _trigger_call_hotkey():
            time.sleep(2.0)
            try:
                import pyautogui
                from jarvis.automations.windows.window_manager import window_manager
                window_manager.focus_window("WhatsApp")
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'shift', 'c')
                logger.info(f"Triggered WhatsApp call hotkey (ctrl+shift+c) for {name}")
            except Exception as e:
                logger.error(f"Error triggering WhatsApp call hotkey: {e}")

        threading.Thread(target=_trigger_call_hotkey, daemon=True).start()

        feedback = f"Initiating WhatsApp call with {name.title()} ({phone_number}), Sir."
        return {
            "success": True,
            "status": "success",
            "recipient": name,
            "phone": phone_number,
            "channel": channel,
            "feedback": feedback,
        }


# Singleton WhatsApp client
whatsapp_client = WhatsAppClient()
