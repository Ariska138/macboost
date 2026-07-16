"""Simple line-based rotating logger (max 1000 lines) for MacBoost."""
from __future__ import annotations

import os

MAX_LINES = 1000


def _log_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "macboost.log")


def log(message: str) -> None:
    """Append one line, keeping the file at most MAX_LINES lines."""
    path = _log_path()
    line = message.replace("\n", " ")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        else:
            lines = []
        lines.append(line)
        if len(lines) > MAX_LINES:
            lines = lines[-MAX_LINES:]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


def read_logs(tail: int = MAX_LINES) -> list[str]:
    """Return last `tail` lines of the log (default: all, max 1000)."""
    path = _log_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        return lines[-tail:] if tail else lines
    except Exception:
        return []


def log_text(tail: int = MAX_LINES) -> str:
    """Render log as Telegram-friendly text block."""
    lines = read_logs(tail)
    if not lines:
        return "_(log kosong)_"
    return "```\n" + "\n".join(lines) + "\n```"
