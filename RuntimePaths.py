"""Runtime path and atomic-file helpers for source and PyInstaller builds."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def source_dir() -> Path:
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return source_dir()


def resource_path(name: str) -> Path:
    return resource_dir() / name


def data_dir() -> Path:
    """Return the writable Image Draw Bot data directory."""
    if is_frozen():
        base = Path((os.environ.get("LOCALAPPDATA") or str(Path.home())))
        root = base / "ImageDrawBot"
    else:
        root = source_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Durably replace a small text file without leaving a half-written config.

    The temporary file is created in the same directory so ``os.replace`` stays
    atomic on Windows. A unique temp name also prevents collisions between a
    normal settings save and a crash/reporting save.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline="",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(str(text))
            stream.flush()
            try:
                os.fsync(stream.fileno())
            except OSError:
                # Some redirected/network locations do not support fsync. The
                # replace is still safer than writing the destination in place.
                pass
            temporary = Path(stream.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def helper_command(helper: str, *args: object) -> list[str]:
    """Build a helper command that works both from source and a frozen EXE.

    In a PyInstaller build we re-launch the same ImageDrawBot.exe with an internal
    helper switch. This avoids depending on python.exe or loose .py files.
    """
    switches = {
        "mouse": "--internal-mouse-probe",
        "target": "--internal-target-probe",
        "palette": "--internal-palette-calibration",
        "exactcolor": "--internal-exact-color-calibration",
    }
    scripts = {
        "mouse": "MouseProbe.py",
        "target": "TargetProbe.py",
        "palette": "GetColorPositions.py",
        "exactcolor": "ExactColorCalibration.py",
    }
    if helper not in switches:
        raise ValueError(f"Unknown helper: {helper}")
    tail = [str(value) for value in args]
    if is_frozen():
        return [sys.executable, switches[helper], *tail]
    return [sys.executable, str(source_dir() / scripts[helper]), *tail]
