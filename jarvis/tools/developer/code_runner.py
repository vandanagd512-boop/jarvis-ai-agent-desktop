"""Execution sandbox for Python scripts and PowerShell commands."""

from __future__ import annotations
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict
from jarvis.core.config import get_settings
from jarvis.core.exceptions import SecurityError
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.CodeRunner")


class CodeRunner:
    """Executes Python code or PowerShell commands safely with timeouts and output capture."""

    def __init__(self, default_timeout: int = 15) -> None:
        self.default_timeout = default_timeout
        self.settings = get_settings()

    def run_python(self, code: str, timeout: int | None = None) -> Dict[str, Any]:
        """Execute a Python snippet in an isolated subprocess."""
        if not self.settings.ALLOW_CODE_EXECUTION:
            raise SecurityError("Code execution is disabled by security configuration.")

        effective_timeout = timeout or self.default_timeout
        t0 = time.time()

        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                script_path = f.name

            proc = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            duration_ms = round((time.time() - t0) * 1000, 2)

            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "duration_ms": duration_ms,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {effective_timeout} seconds.",
                "exit_code": -1,
                "duration_ms": round((time.time() - t0) * 1000, 2),
            }
        except Exception as exc:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "duration_ms": round((time.time() - t0) * 1000, 2),
            }

    def run_powershell(self, command: str, timeout: int | None = None) -> Dict[str, Any]:
        """Execute a PowerShell command safely."""
        if not self.settings.ALLOW_CODE_EXECUTION:
            raise SecurityError("Command execution is disabled by security configuration.")

        effective_timeout = timeout or self.default_timeout
        t0 = time.time()

        try:
            cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            duration_ms = round((time.time() - t0) * 1000, 2)

            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "duration_ms": duration_ms,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"PowerShell command timed out after {effective_timeout} seconds.",
                "exit_code": -1,
                "duration_ms": round((time.time() - t0) * 1000, 2),
            }
        except Exception as exc:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "duration_ms": round((time.time() - t0) * 1000, 2),
            }


# Singleton code runner instance
code_runner = CodeRunner()
