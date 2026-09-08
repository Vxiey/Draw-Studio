"""Profile-isolated persistent storage helpers for Draw Studio.

Step 9 centralizes every profile-derived filename so Paint, Gartic, Skribbl and
other targets cannot accidentally reuse another profile's calibration/cache.
The generic profile keeps the historic filenames for backwards compatibility.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from RuntimePaths import data_dir


def safe_profile_key(profile_key: str | None) -> str:
    text = str(profile_key or "generic").strip().lower().replace(" ", "-")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in text)[:80]
    return safe or "generic"


def profile_palette_file(profile_key: str | None) -> Path:
    key = safe_profile_key(profile_key)
    return data_dir() / ("calibration.json" if key == "generic" else f"calibration-{key}.json")


def profile_settings_file(profile_key: str | None) -> Path:
    key = safe_profile_key(profile_key)
    return data_dir() / ("settings.json" if key == "generic" else f"settings-{key}.json")


def profile_timing_file(profile_key: str | None) -> Path:
    return data_dir() / f"draw-time-calibration-{safe_profile_key(profile_key)}.json"


def profile_auto_tuner_feedback_file(profile_key: str | None) -> Path:
    """Step 12 local strategy-learning database, isolated per target profile."""
    return data_dir() / f"auto-tuner-feedback-{safe_profile_key(profile_key)}.json"


def profile_correction_history_file(profile_key: str | None) -> Path:
    """Step 16 local before/after correction history, isolated per target profile."""
    return data_dir() / f"correction-history-{safe_profile_key(profile_key)}.json"


def profile_layout_cache_file(profile_key: str | None) -> Path:
    return data_dir() / f"layout-fingerprints-v2-{safe_profile_key(profile_key)}.json"


def profile_verified_color_file(profile_key: str | None) -> Path:
    return data_dir() / f"verified-colors-{safe_profile_key(profile_key)}.json"


def _profile_context_files(profile_key: str | None, palette_path: Path | None = None) -> tuple[Path, ...]:
    """Files that can change the meaning of a cached color/tool operation."""
    key = safe_profile_key(profile_key)
    root = data_dir()
    files = [Path(palette_path) if palette_path is not None else profile_palette_file(key)]
    files.append(root / f"exact-colors-{key}.json")
    if key == "microsoft-paint":
        files.append(root / "paint-tools-microsoft-paint.json")
        files.append(root / "paint-tools.json")  # legacy source; harmless after migration
    else:
        files.append(root / f"app-tools-{key}.json")
    return tuple(files)


def calibration_context_fingerprint(profile_key: str | None, *, workflow: str = "",
                                    palette_path: Path | None = None,
                                    extras: Iterable[str] = ()) -> str:
    """Stable fingerprint for profile calibration context.

    Persistent verified-color cache entries are valid only while this fingerprint
    matches. Recalibrating the palette/tools/exact-color controls invalidates old
    verified values without deleting another profile's cache.
    """
    key = safe_profile_key(profile_key)
    digest = hashlib.sha256()
    digest.update(f"profile:{key}\nworkflow:{str(workflow)}\n".encode("utf-8"))
    for item in extras:
        digest.update(f"extra:{item}\n".encode("utf-8"))
    for path in _profile_context_files(key, palette_path):
        digest.update(f"file:{path.name}:".encode("utf-8"))
        try:
            payload = path.read_bytes()
        except OSError:
            digest.update(b"<missing>\n")
        else:
            digest.update(hashlib.sha256(payload).digest())
            digest.update(b"\n")
    return digest.hexdigest()[:24]
