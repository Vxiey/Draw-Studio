"""Local version-history helpers for Draw Studio.

The functions are deterministic and local-only. They read bundled markdown files
from the source tree or a PyInstaller onedir bundle; they never use the network.
"""
from __future__ import annotations

from pathlib import Path
import sys

from Version import APP_VERSION


CANDIDATE_FILES = ("VERSION-HISTORY.md", "docs/VERSION-HISTORY.md")


def candidate_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    roots.append(Path(__file__).resolve().parent)
    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        key = str(root)
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return tuple(unique)


def find_version_history_file() -> Path | None:
    for root in candidate_roots():
        for rel in CANDIDATE_FILES:
            path = root / rel
            if path.is_file():
                return path
    return None


def read_version_history(max_chars: int = 70000) -> str:
    path = find_version_history_file()
    if path is None:
        return f"Draw Studio {APP_VERSION}\n\nVersion history file was not found in this build."
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return f"Draw Studio {APP_VERSION}\n\nCould not read version history: {error}"
    text = text.strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n\n[Version history truncated in the viewer.]"
    return text + "\n"


def has_version_history() -> bool:
    return find_version_history_file() is not None
