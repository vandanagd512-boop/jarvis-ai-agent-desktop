"""Interactive terminal user interface for JARVIS using Rich."""

from __future__ import annotations
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from jarvis.brain.router import action_router
from jarvis.core.config import get_settings
from jarvis.core.context import runtime_context
from jarvis.memory.semantic_store import semantic_store
from jarvis.monitoring.sys_monitor import sys_monitor
from jarvis.plugins.plugin_manager import plugin_manager
from jarvis.voice.listener import VoiceState, voice_listener
from jarvis.voice.tts import tts_engine
from jarvis.workflow.workflow_engine import workflow_engine

console = Console()


class JarvisCLI:
    """Terminal command interface with rich panels and formatting."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def print_banner(self) -> None:
        """Render stylish startup banner."""
        banner_text = Text()
        banner_text.append("   __ ___ _____  __ _____ ___\n", style="bold cyan")
        banner_text.append("  / // / // / _ \\/ // / _ (_-<\n", style="bold cyan")
        banner_text.append(" /_//_/\\_,_/\\___/_/ /_\\_,_/___/\n", style="bold cyan")
        banner_text.append(f"\n   Windows AI Desktop Assistant [v{self.settings.APP_VERSION}]\n", style="bold white")
        banner_text.append("   Type /help for command list or speak/type directly.\n", style="italic dim")

        mem = sys_monitor.get_memory_status()
        disk = sys_monitor.get_disk_usage("C:")
        battery = sys_monitor.get_battery_status()

        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="right")
        grid.add_row(
            f"[bold green]● System Online[/bold green] | OS: [cyan]{runtime_context.os_name}[/cyan]",
            f"RAM: [yellow]{mem.used_gb}/{mem.total_gb} GB ({mem.load_percent}%)[/yellow] | Battery: [magenta]{battery.status_text if battery else 'N/A'}[/magenta]",
        )

        panel = Panel(
            grid,
            title="[bold cyan]J.A.R.V.I.S.[/bold cyan]",
            border_style="bright_blue",
        )
        console.print(banner_text)
        console.print(panel)

    def print_help(self) -> None:
        """Display help table."""
        table = Table(title="Available Slash Commands", border_style="cyan")
        table.add_column("Command", style="bold yellow")
        table.add_column("Description", style="white")

        table.add_row("/status", "Display real-time hardware metrics and active processes")
        table.add_row("/voice on|off", "Toggle continuous microphone listening")
        table.add_row("/tools", "List all registered system and plugin tools")
        table.add_row("/workflows", "List and execute automated multi-step routines")
        table.add_row("/plugins", "View status of discovered plugins")
        table.add_row("/notes", "List stored productivity notes")
        table.add_row("/reminders", "List pending scheduled reminders")
        table.add_row("/clear", "Clear the terminal screen")
        table.add_row("/quit or /exit", "Shut down JARVIS safely")

        console.print(table)

    def show_status(self) -> None:
        """Print full telemetry."""
        summary = sys_monitor.get_summary()
        console.print(Panel(str(summary), title="[bold green]System Telemetry[/bold green]"))

    def run_interactive_loop(self) -> None:
        """Run blocking read-eval-print loop with background voice listener."""
        self.print_banner()

        # Automatically start continuous voice listener in background
        try:
            voice_listener.start()
            console.print("[bold green]● Background Voice Engine: ONLINE[/bold green] (Speak into microphone or type below)\n")
        except Exception as v_err:
            console.print(f"[dim]Voice listener note: {v_err}[/dim]\n")

        while True:
            try:
                user_input = console.input("\n[bold cyan]Sir > [/bold cyan]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold yellow]Shutting down JARVIS. Good day, Sir.[/bold yellow]")
                voice_listener.stop()
                break

            if not user_input:
                continue

            # Command handling
            cmd_lower = user_input.lower()
            if cmd_lower in ("/exit", "/quit", "quit", "exit"):
                console.print("[bold yellow]JARVIS offline. Good day, Sir.[/bold yellow]")
                break

            elif cmd_lower == "/help":
                self.print_help()

            elif cmd_lower == "/clear":
                console.clear()
                self.print_banner()

            elif cmd_lower == "/status":
                self.show_status()

            elif cmd_lower.startswith("/voice"):
                parts = cmd_lower.split()
                if len(parts) > 1 and parts[1] == "on":
                    voice_listener.start()
                    console.print("[bold green]Voice listener enabled. Speak 'Jarvis' anytime.[/bold green]")
                elif len(parts) > 1 and parts[1] == "off":
                    voice_listener.stop()
                    console.print("[bold red]Voice listener disabled.[/bold red]")
                else:
                    state_str = "ENABLED" if voice_listener._is_active else "DISABLED"
                    console.print(f"Voice listener is currently: [bold]{state_str}[/bold]")

            elif cmd_lower == "/tools":
                table = Table(title="Registered Tools", border_style="blue")
                table.add_column("Tool Name", style="bold cyan")
                for name in sorted(action_router._tools.keys()):
                    table.add_row(name)
                console.print(table)

            elif cmd_lower == "/plugins":
                plugins = plugin_manager.list_plugins()
                console.print(Panel(str(plugins), title="Loaded Plugins"))

            elif cmd_lower == "/notes":
                notes = semantic_store.list_notes()
                table = Table(title="Stored Notes", border_style="magenta")
                table.add_column("Title", style="bold yellow")
                table.add_column("Content", style="white")
                table.add_column("Tags", style="dim")
                for n in notes:
                    table.add_row(n["title"], n["content"][:60], n["tags"])
                console.print(table)

            elif cmd_lower == "/reminders":
                rems = semantic_store.get_pending_reminders()
                table = Table(title="Pending Reminders", border_style="yellow")
                table.add_column("Title", style="bold cyan")
                table.add_column("Due At", style="white")
                for r in rems:
                    table.add_row(r["title"], r["due_at"])
                console.print(table)

            else:
                # Regular user query -> process via action router
                with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
                    result = action_router.process_query(user_input, conversation_id="cli_session")

                response_text = result["response"]
                console.print(f"[bold cyan]JARVIS:[/bold cyan] {response_text}")

                if result.get("actions_executed"):
                    for act in result["actions_executed"]:
                        res_val = act.get("result", "")
                        if "stdout" in res_val and len(res_val) > 10:
                            try:
                                import ast
                                parsed = ast.literal_eval(res_val)
                                if isinstance(parsed, dict) and parsed.get("stdout"):
                                    console.print(Panel(parsed["stdout"].strip(), title=f"[dim]Output ({act['action']})[/dim]"))
                                    continue
                            except Exception:
                                pass
                        console.print(f"  [dim green]✔ Executed:[/dim green] [bold]{act['action']}[/bold] -> {res_val[:120]}")


# Singleton CLI instance
jarvis_cli = JarvisCLI()
