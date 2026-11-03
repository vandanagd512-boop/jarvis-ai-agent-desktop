"""Comprehensive application and web service launcher for Windows desktop."""

from __future__ import annotations
import os
import shutil
import subprocess
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.AppLauncher")

# Registry of common system applications, desktop tools, and web services
KNOWN_TARGETS: Dict[str, str] = {
    # Social & Communications
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "youtube": "https://www.youtube.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "gmail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "telegram": "https://web.telegram.org",
    "discord": "https://discord.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "facebook": "https://www.facebook.com",
    "spotify": "spotify:",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "maps": "https://maps.google.com",

    # Windows Standard Desktop Tools
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "my computer": "explorer.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "settings": "ms-settings:",
    "control panel": "control.exe",
    "control": "control.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
}


class AppLauncher:
    """Manages launching of Windows desktop applications, URI schemes, and web platforms."""

    def launch(
        self,
        target: str,
        arguments: Optional[List[str]] = None,
        allow_domain_fallback: bool = False,
    ) -> Dict[str, Any]:
        """Launch an application or web service by name, path, or URI."""
        cleaned_target = target.strip().lower()
        args = arguments or []

        # 1. Resolve target from registry
        resolved = KNOWN_TARGETS.get(cleaned_target, target)

        logger.info(f"Launching target '{target}' -> Resolved as '{resolved}'")

        # 2. If it's a web URL
        if resolved.startswith(("http://", "https://")):
            try:
                webbrowser.open(resolved)
                return {
                    "success": True,
                    "target": target,
                    "resolved": resolved,
                    "type": "web_url",
                    "message": f"Opening {target.title()} in your browser: {resolved}",
                }
            except Exception as exc:
                logger.error(f"Failed to open web URL '{resolved}': {exc}")

        # 3. If it's a URI scheme (e.g. ms-settings:, spotify:)
        if ":" in resolved and not os.path.isabs(resolved):
            try:
                os.startfile(resolved)
                return {
                    "success": True,
                    "target": target,
                    "resolved": resolved,
                    "type": "uri_scheme",
                    "message": f"Successfully launched {target.title()} ({resolved})",
                }
            except Exception as uri_err:
                logger.warning(f"URI scheme '{resolved}' failed: {uri_err}")

        # 4. Try native executable process launch
        try:
            full_command = [resolved] + args
            proc = subprocess.Popen(
                full_command,
                shell=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            )
            return {
                "success": True,
                "target": target,
                "resolved": resolved,
                "pid": proc.pid,
                "type": "process",
                "message": f"Successfully launched {target.title()} (PID: {proc.pid})",
            }
        except Exception:
            # 5. Fallback to Windows Shell association
            try:
                os.startfile(resolved)
                return {
                    "success": True,
                    "target": target,
                    "resolved": resolved,
                    "type": "shell_association",
                    "message": f"Successfully opened {target.title()} via Windows Shell",
                }
            except Exception:
                pass

        # 6. Fallback: If explicitly requested or target looks like a domain (e.g. flipkart.com)
        if allow_domain_fallback or any(cleaned_target.endswith(tld) for tld in [".com", ".org", ".net", ".io", ".in", ".co"]):
            domain = cleaned_target if "." in cleaned_target else f"www.{cleaned_target}.com"
            fallback_url = f"https://{domain}" if not domain.startswith("http") else domain
            logger.info(f"Attempting web domain fallback for '{cleaned_target}': {fallback_url}")
            try:
                webbrowser.open(fallback_url)
                return {
                    "success": True,
                    "target": target,
                    "resolved": fallback_url,
                    "type": "domain_fallback",
                    "message": f"Opened {target.title()} via {fallback_url}",
                }
            except Exception:
                pass

        return {
            "success": False,
            "target": target,
            "error": f"Could not find or launch application/service: {target}",
            "message": f"Sorry Sir, I could not find '{target}'.",
        }

    def list_known_apps(self) -> List[str]:
        """Return list of recognizable app shortcut names."""
        return sorted(list(KNOWN_TARGETS.keys()))


# Singleton instance
app_launcher = AppLauncher()
KNOWN_APPS = KNOWN_TARGETS  # Backward compatibility alias
