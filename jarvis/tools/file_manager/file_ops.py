"""Advanced filesystem management, search, organization, and checksums."""

from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.FileOps")

CATEGORY_EXTENSIONS: Dict[str, List[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".md"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"],
    "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml", ".cpp", ".c", ".rs"],
}


class FileManager:
    """Manages file searches, reading/writing, categorization, and integrity verification."""

    def search_files(
        self,
        directory: str,
        pattern: str = "*",
        max_results: int = 50,
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search files by glob pattern."""
        target_dir = Path(directory).expanduser().resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            logger.warning(f"Directory '{directory}' does not exist.")
            return []

        results: List[Dict[str, Any]] = []
        iterator = target_dir.rglob(pattern) if recursive else target_dir.glob(pattern)

        for p in iterator:
            if len(results) >= max_results:
                break
            try:
                stat = p.stat()
                results.append({
                    "name": p.name,
                    "path": str(p),
                    "is_dir": p.is_dir(),
                    "size_bytes": stat.st_size if not p.is_dir() else 0,
                    "modified": stat.st_mtime,
                })
            except Exception:
                continue

        logger.info(f"Found {len(results)} matches for pattern '{pattern}' in '{directory}'")
        return results

    def read_file_content(self, file_path: str, max_lines: int = 500) -> Dict[str, Any]:
        """Read text contents of a file safely."""
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return {"success": False, "error": f"File '{file_path}' does not exist."}
        if path.is_dir():
            return {"success": False, "error": f"Path '{file_path}' is a directory."}

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)
            return {
                "success": True,
                "path": str(path),
                "content": content,
                "lines_read": len(lines),
            }
        except Exception as exc:
            logger.error(f"Error reading file '{file_path}': {exc}")
            return {"success": False, "error": str(exc)}

    def write_file_content(self, file_path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """Write or append text content to a file."""
        path = Path(file_path).expanduser().resolve()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Successfully {'appended to' if append else 'wrote to'} file: {path}")
            return {"success": True, "path": str(path), "bytes_written": len(content)}
        except Exception as exc:
            logger.error(f"Error writing to file '{file_path}': {exc}")
            return {"success": False, "error": str(exc)}

    def organize_directory(self, directory: str) -> Dict[str, Any]:
        """Organize files in directory into categorical subfolders."""
        target_dir = Path(directory).expanduser().resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            return {"success": False, "error": f"Directory '{directory}' does not exist."}

        moved_count: Dict[str, int] = {cat: 0 for cat in CATEGORY_EXTENSIONS}
        moved_count["Other"] = 0

        for item in target_dir.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                matched_category = "Other"
                for cat, extensions in CATEGORY_EXTENSIONS.items():
                    if ext in extensions:
                        matched_category = cat
                        break

                dest_dir = target_dir / matched_category
                dest_dir.mkdir(exist_ok=True)
                dest_file = dest_dir / item.name

                try:
                    shutil.move(str(item), str(dest_file))
                    moved_count[matched_category] += 1
                except Exception as exc:
                    logger.warning(f"Could not move '{item.name}': {exc}")

        logger.info(f"Organized directory '{directory}': {moved_count}")
        return {"success": True, "directory": str(target_dir), "summary": moved_count}

    def calculate_file_checksum(self, file_path: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """Calculate cryptographic hash of a file."""
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            return {"success": False, "error": f"File '{file_path}' not found."}

        hasher = hashlib.new(algorithm)
        try:
            with open(path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    hasher.update(chunk)
            checksum = hasher.hexdigest()
            return {"success": True, "path": str(path), "algorithm": algorithm, "checksum": checksum}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


# Singleton file manager instance
file_manager = FileManager()
