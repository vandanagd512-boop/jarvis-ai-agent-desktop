"""Main entry point for JARVIS AI Desktop Assistant."""

from __future__ import annotations
import argparse
import signal
import sys
import threading
import time
import webbrowser

from jarvis.core.config import get_settings
from jarvis.core.events import Event, EventType, event_bus
from jarvis.core.logger import get_logger, setup_logging
from jarvis.memory.database import init_db
from jarvis.plugins.plugin_manager import plugin_manager
from jarvis.ui.cli import jarvis_cli
from jarvis.voice.listener import voice_listener
from jarvis.voice.tts import tts_engine
from jarvis.workflow.predefined_workflows import register_predefined_workflows

logger = get_logger("JARVIS.Main")


def handle_shutdown(signum, frame):
    """Graceful shutdown signal handler."""
    print("\n[JARVIS] Terminating services gracefully...")
    voice_listener.stop()
    tts_engine.stop()
    event_bus.publish_sync(Event(event_type=EventType.SYSTEM_SHUTDOWN))
    sys.exit(0)


def initialize_subsystems() -> None:
    """Boot and verify all core subsystems."""
    settings = get_settings()
    setup_logging(log_dir=settings.LOG_DIR, log_level=settings.LOG_LEVEL)

    logger.info(f"Initializing {settings.APP_NAME} v{settings.APP_VERSION} in {settings.ENVIRONMENT} mode.")

    # 1. Database and persistence
    init_db()

    # 2. Plugins
    plugin_manager.discover_and_load_all()

    # 3. Predefined workflows
    register_predefined_workflows()

    # 4. Notify startup event
    event_bus.publish_sync(Event(event_type=EventType.SYSTEM_STARTUP, payload={"version": settings.APP_VERSION}))
    logger.info("All JARVIS subsystems initialized successfully.")


def open_browser_delayed(url: str, delay: float = 1.2) -> None:
    """Open default browser to the web dashboard after server starts."""
    def _run():
        time.sleep(delay)
        print(f"[JARVIS] Opening web dashboard in browser: {url}")
        webbrowser.open(url)
    threading.Thread(target=_run, daemon=True).start()


def main() -> None:
    """Parse CLI arguments and launch selected UI interface."""
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    parser = argparse.ArgumentParser(description="JARVIS - Production-Ready Windows AI Desktop Assistant")
    parser.add_argument(
        "--mode",
        choices=["web", "cli", "voice", "api"],
        default="web",
        help="Execution mode: futuristic Web Dashboard (default), interactive CLI, voice daemon, or headless API.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="API/Web server host")
    parser.add_argument("--port", type=int, default=8765, help="API/Web server port")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Bootstrap subsystems
    initialize_subsystems()

    if args.mode == "web":
        import uvicorn
        from jarvis.ui.api_server import app

        local_url = f"http://127.0.0.1:{args.port}"
        print(f"\n=======================================================")
        print(f"  J.A.R.V.I.S. Production Web Dashboard")
        print(f"  Local PC:      {local_url}")
        print(f"  Phone / Wi-Fi: http://10.60.181.160:{args.port}")
        print(f"  Hybrid Voice:  In-browser voice & background wake-word")
        print(f"=======================================================\n")

        # Start desktop wake-word listener in background
        voice_listener.start()

        if not args.no_browser:
            open_browser_delayed(local_url)

        uvicorn.run(app, host=args.host, port=args.port, log_level="info")

    elif args.mode == "cli":
        jarvis_cli.run_interactive_loop()

    elif args.mode == "voice":
        voice_listener.start()
        print("[JARVIS] Running in continuous voice listening mode. Speak 'Jarvis' to interact. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)

    elif args.mode == "api":
        import uvicorn
        from jarvis.ui.api_server import app
        print(f"[JARVIS] Starting API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
