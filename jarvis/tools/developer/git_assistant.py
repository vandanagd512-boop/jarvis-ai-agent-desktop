"""Git repository assistant and inspection tools."""

from __future__ import annotations
from pathlib import Path
import subprocess
from typing import Any, Dict, List
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.Git")


class GitAssistant:
    """Manages Git repository inspection, branches, status, and commits."""

    def _run_git(self, repo_dir: str, args: List[str]) -> Dict[str, Any]:
        """Run git command in specified repository directory."""
        try:
            path = Path(repo_dir).expanduser().resolve()
            proc = subprocess.run(
                ["git"] + args,
                cwd=str(path),
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "exit_code": proc.returncode,
            }
        except Exception as exc:
            return {"success": False, "stdout": "", "stderr": str(exc), "exit_code": -1}

    def get_status(self, repo_dir: str = ".") -> Dict[str, Any]:
        """Query repository working tree status."""
        res = self._run_git(repo_dir, ["status", "--short", "--branch"])
        return {
            "success": res["success"],
            "status_text": res["stdout"],
            "error": res["stderr"] if not res["success"] else None,
        }

    def get_current_branch(self, repo_dir: str = ".") -> str:
        """Get name of currently checked-out branch."""
        res = self._run_git(repo_dir, ["rev-parse", "--abbrev-ref", "HEAD"])
        return res["stdout"] if res["success"] else "Unknown"

    def get_recent_commits(self, repo_dir: str = ".", count: int = 5) -> List[Dict[str, str]]:
        """Fetch summary of recent commit messages and hashes."""
        res = self._run_git(repo_dir, ["log", f"-n{count}", "--pretty=format:%h|%an|%ar|%s"])
        if not res["success"] or not res["stdout"]:
            return []

        commits = []
        for line in res["stdout"].splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "subject": parts[3],
                })
        return commits


# Singleton git assistant instance
git_assistant = GitAssistant()
