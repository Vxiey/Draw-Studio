"""Progressive execution ordering for Draw Studio v1.0.21.

The planner remains pure: it only reorders already-safe execution paths. It does
not move the mouse, read files, touch Tk, or change calibration. DrawBot uses the
returned sequence so a drawing becomes recognizable early: broad fill/foundation
paths first, important contours second, tiny details last.
"""
from __future__ import annotations

import math
from typing import Sequence, Any

Point = tuple[int, int]
Path = tuple[Point, ...]

PROGRESSIVE_RENDERING_MODES = ("Auto", "On", "Off")
_PHASE_ORDER = {"foundation": 0, "contour": 1, "details": 2}
_PHASE_LABELS = {
    "foundation": "large forms",
    "contour": "important contours",
    "details": "small details",
}


def validate_progressive_rendering(value: str) -> str:
    if value not in PROGRESSIVE_RENDERING_MODES:
        raise ValueError("Choose a valid progressive rendering mode.")
    return value


def progressive_enabled(value: str, *, drawing_mode: str = "", time_budget_active: bool = False) -> bool:
    validate_progressive_rendering(value)
    if value == "On":
        return True
    if value == "Off":
        return False
    # Auto is deliberately conservative for exact Paint sketches, but enabled
    # for the fast approximate renderers where a recognizable early result is
    # more useful than strict colour-by-colour completion.
    return drawing_mode == "Shape paths" or bool(time_budget_active)


def _path_len(path: Sequence[Point]) -> float:
    if len(path) < 2:
        return 0.0
    return sum(math.hypot(float(b[0] - a[0]), float(b[1] - a[1])) for a, b in zip(path, path[1:]))


def _bounds(path: Sequence[Point]) -> tuple[int, int, int, int]:
    xs = [int(p[0]) for p in path]
    ys = [int(p[1]) for p in path]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_area(path: Sequence[Point]) -> int:
    x0, y0, x1, y1 = _bounds(path)
    return max(1, x1 - x0 + 1) * max(1, y1 - y0 + 1)


def _normalize_phase(phase: Any, path: Sequence[Point]) -> str:
    if phase in _PHASE_ORDER:
        return str(phase)
    if len(path) <= 1:
        return "details"
    length = _path_len(path)
    area = _bbox_area(path)
    if area >= 900 or length >= 80:
        return "foundation"
    if len(path) == 2 and (length >= 18 or area >= 80):
        return "contour"
    return "details"


def _importance(path: Sequence[Point], phase: str, serial: int) -> float:
    length = _path_len(path)
    area = _bbox_area(path)
    if phase == "foundation":
        return area * 0.18 + length * 1.4 - serial * 1e-6
    if phase == "contour":
        return length * 1.8 + area * 0.03 - serial * 1e-6
    return length + (3.0 if len(path) == 1 else 0.0) - serial * 1e-6


def build_progressive_sequence(execution_groups: Sequence[Sequence[Path]], *,
                               phase_hints: Sequence[Sequence[str]] | None = None,
                               enabled: bool = True) -> tuple[list[dict], dict]:
    """Return a pass-based execution sequence and metadata.

    Each sequence item is a small dict with color_index, path, phase and serial.
    The original per-colour execution groups remain unchanged for preview and
    legacy code.  When disabled an empty sequence is returned with compatible
    metadata.
    """
    total = sum(len(paths) for paths in execution_groups)
    if not enabled or total <= 0:
        return [], {
            "progressive_enabled": False,
            "progressive_sequence_paths": 0,
            "progressive_foundation_paths": 0,
            "progressive_contour_paths": 0,
            "progressive_detail_paths": 0,
        }

    entries: list[dict] = []
    serial = 0
    counts = {"foundation": 0, "contour": 0, "details": 0}
    hints = phase_hints or []
    for color_index, paths in enumerate(execution_groups):
        color_hints = hints[color_index] if color_index < len(hints) else []
        for local_index, path in enumerate(paths):
            path = tuple(path)
            if not path:
                continue
            hint = color_hints[local_index] if local_index < len(color_hints) else None
            phase = _normalize_phase(hint, path)
            counts[phase] += 1
            entries.append({
                "color_index": int(color_index),
                "path": path,
                "phase": phase,
                "phase_label": _PHASE_LABELS[phase],
                "serial": serial,
                "importance": _importance(path, phase, serial),
            })
            serial += 1

    entries.sort(key=lambda item: (_PHASE_ORDER[item["phase"]], -float(item["importance"]), int(item["color_index"]), int(item["serial"])))
    # Remove score-only field before it gets stored in the plan. Tests and logs
    # should not depend on floating point tie-breaker values.
    sequence = [{k: v for k, v in item.items() if k != "importance"} for item in entries]
    return sequence, {
        "progressive_enabled": True,
        "progressive_sequence_paths": len(sequence),
        "progressive_foundation_paths": counts["foundation"],
        "progressive_contour_paths": counts["contour"],
        "progressive_detail_paths": counts["details"],
        "progressive_phase_order": "large forms → important contours → details",
    }
