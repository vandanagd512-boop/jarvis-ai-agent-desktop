"""System power management (Lock, Sleep, Shutdown, Restart)."""

import ctypes
import subprocess
from jarvis.core.config import get_settings
from jarvis.core.exceptions import SecurityError
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.PowerManager")


class PowerManager:
    """Manages workstation lock and power state transitions safely."""

    @staticmethod
    def lock_workstation() -> bool:
        """Lock the current Windows workstation immediately."""
        logger.info("Executing workstation lock.")
        return bool(ctypes.windll.user32.LockWorkStation())

    @staticmethod
    def sleep_system() -> bool:
        """Put workstation to sleep."""
        settings = get_settings()
        if not settings.ALLOW_SYSTEM_POWER_COMMANDS:
            raise SecurityError("System power commands are disabled by configuration.")
        logger.info("Suspending workstation to sleep state.")
        # PowrProf.SetSuspendState(bHibernate=False, bForce=False, bWakeupEventsDisabled=False)
        return bool(ctypes.windll.PowrProf.SetSuspendState(0, 1, 0))

    @staticmethod
    def schedule_shutdown(delay_seconds: int = 60) -> bool:
        """Schedule system shutdown with a countdown timer."""
        settings = get_settings()
        if not settings.ALLOW_SYSTEM_POWER_COMMANDS:
            raise SecurityError("System power commands are disabled by configuration.")
        logger.warning(f"Scheduling system shutdown in {delay_seconds} seconds.")
        res = subprocess.run(
            ["shutdown", "/s", "/t", str(delay_seconds)],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return res.returncode == 0

    @staticmethod
    def schedule_restart(delay_seconds: int = 60) -> bool:
        """Schedule system restart with a countdown timer."""
        settings = get_settings()
        if not settings.ALLOW_SYSTEM_POWER_COMMANDS:
            raise SecurityError("System power commands are disabled by configuration.")
        logger.warning(f"Scheduling system restart in {delay_seconds} seconds.")
        res = subprocess.run(
            ["shutdown", "/r", "/t", str(delay_seconds)],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return res.returncode == 0

    @staticmethod
    def abort_shutdown() -> bool:
        """Abort a pending scheduled shutdown or restart."""
        logger.info("Aborting scheduled shutdown/restart.")
        res = subprocess.run(
            ["shutdown", "/a"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return res.returncode == 0


# Singleton instance
power_manager = PowerManager()
