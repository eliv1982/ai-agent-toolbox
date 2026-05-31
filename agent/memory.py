"""Persistent conversation memory stored in memory.json."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MEMORY_FILE = PROJECT_ROOT / "memory.json"


def _resolve_path(memory_file: Path | None) -> Path:
    return memory_file or DEFAULT_MEMORY_FILE


def load_memory(memory_file: Path | None = None) -> list[dict[str, Any]]:
    """Load memory entries from JSON file."""
    path = _resolve_path(memory_file)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_memory(entries: list[dict[str, Any]], memory_file: Path | None = None) -> None:
    path = _resolve_path(memory_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(entries, fh, ensure_ascii=False, indent=2)


def add_memory_entry(
    user_message: str = "",
    assistant_response: str = "",
    note: str = "",
    memory_file: Path | None = None,
) -> dict[str, Any]:
    """Append a new memory entry and persist it."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_message": user_message,
        "assistant_response": assistant_response,
        "note": note,
    }
    entries = load_memory(memory_file)
    entries.append(entry)
    _save_memory(entries, memory_file)
    return entry


def clear_memory(memory_file: Path | None = None) -> None:
    """Remove all memory entries."""
    _save_memory([], memory_file)


def summarize_memory_for_prompt(
    limit: int = 8,
    memory_file: Path | None = None,
) -> str:
    """Build a short summary of recent memory for the agent prompt."""
    entries = load_memory(memory_file)
    if not entries:
        return "История диалога пуста."

    recent = entries[-limit:]
    lines: list[str] = []
    for item in recent:
        ts = item.get("timestamp", "")
        user_msg = item.get("user_message", "")
        assistant_msg = item.get("assistant_response", "")
        note = item.get("note", "")
        if user_msg or assistant_msg:
            lines.append(f"[{ts}] User: {user_msg}")
            if assistant_msg:
                lines.append(f"[{ts}] Assistant: {assistant_msg}")
        elif note:
            lines.append(f"[{ts}] Note: {note}")
    return "\n".join(lines)
