"""Time-budget and target-stroke controls for Draw Studio v1.0.20.

This module is intentionally pure and deterministic. It does not touch Tk,
mouse input, files, network, GPU state or calibration.  DrawBot uses it to turn
user-facing budget controls into conservative planning caps before the guarded
mouse is armed.
"""
from __future__ import annotations

import math
import heapq
from typing import Sequence

Point = tuple[int, int]
Path = tuple[Point, ...]

TIME_BUDGET_MODES = (
    "Manual", "Custom",
    "Gartic Phone Fast", "Gartic Phone Normal", "Gartic Phone Slow",
    "Skribbl Default", "Skribbl 60", "Skribbl 120", "Skribbl 150",
    "Emergency 30 s", "Ultra Fast 60 s", "Detailed 120 s", "Maximum 300 s",
    "Unlimited / Accuracy",
    # Legacy names remain valid for old profile/settings files.
    "Unlimited", "30 sec", "60 sec", "90 sec", "2 min", "5 min", "10 min",
)
TARGET_STROKE_COUNTS = ("Auto", "500", "1000", "2500", "5000", "10000", "Custom", "Unlimited")

_TIME_SECONDS = {
    "30 sec": 30,
    "60 sec": 60,
    "90 sec": 90,
    "2 min": 120,
    "5 min": 300,
    "10 min": 600,
}


def validate_time_budget_mode(value: str) -> str:
    if value not in TIME_BUDGET_MODES:
        raise ValueError("Choose a valid time budget mode.")
    return value


def validate_target_stroke_count(value: str) -> str:
    if value not in TARGET_STROKE_COUNTS:
        raise ValueError("Choose a valid target stroke count.")
    return value


def parse_custom_stroke_count(value: str | int | None) -> int:
    try:
        count = int(str(value or "").strip())
    except (TypeError, ValueError):
        raise ValueError("Custom target stroke count must be a whole number.") from None
    if not 50 <= count <= 50000:
        raise ValueError("Custom target stroke count must be 50–50000.")
    return count


def resolve_time_budget_seconds(mode: str, manual_seconds: int | float) -> tuple[int, bool]:
    """Return usable render seconds and whether deadline adaptation is active.

    New v1.0.119 presets and legacy generic timers reserve time before the real game deadline. Legacy
    Manual keeps its historical behavior for compatibility.
    """
    validate_time_budget_mode(mode)
    from TimeBudgetEngine import resolve_budget
    meta = resolve_budget(mode, manual_seconds, "Auto")
    if meta.get("unlimited"):
        return 3600, False
    return max(1, int(round(float(meta.get("render_budget_seconds") or manual_seconds)))), bool(meta.get("active"))


def resolve_time_budget_details(mode: str, manual_seconds: int | float, reserve="Auto") -> dict:
    validate_time_budget_mode(mode)
    from TimeBudgetEngine import resolve_budget
    return resolve_budget(mode, manual_seconds, reserve)


def _auto_count_from_time(seconds: int, speed: str, drawing_mode: str, *, preview: bool = False) -> int:
    """Conservative path-count target derived from a visible time budget.

    It is deliberately not a guarantee; exact draw time still depends on path
    length, precision, palette changes and Fill/tool actions.  The final estimate
    remains the hard safety gate in DrawBot.
    """
    speed = str(speed or "Balanced")
    if speed == "Fast":
        paths_per_second = 8.0
    elif speed == "Safe":
        paths_per_second = 3.8
    else:
        paths_per_second = 5.7
    mode = str(drawing_mode or "")
    if mode == "Shape paths":
        paths_per_second *= 1.20
    elif mode == "Dots":
        paths_per_second *= 0.55
    elif mode.startswith("Smart paths"):
        paths_per_second *= 0.95
    # Reserve time for countdown, palette/tool changes, target activation and
    # small planner inaccuracies. Preview gets a tighter cap so it appears fast.
    drawable_seconds = max(2.0, float(seconds) - (8.0 if not preview else 2.0))
    target = int(drawable_seconds * paths_per_second)
    floor = 120 if not preview else 80
    ceiling = 12000 if not preview else 3000
    return max(floor, min(ceiling, target))


def resolve_target_stroke_count(value: str, custom_value: str | int | None = None, *,
                                time_budget_mode: str = "Manual",
                                effective_time_seconds: int = 180,
                                speed: str = "Balanced",
                                drawing_mode: str = "Smart paths (recommended)",
                                preview: bool = False) -> tuple[int | None, dict]:
    """Resolve a target path cap and explanatory metadata.

    None means unlimited.  Auto only creates a cap when a preset time budget is
    active; Manual+Auto preserves existing behaviour.
    """
    validate_target_stroke_count(value)
    validate_time_budget_mode(time_budget_mode)
    source = value
    if value == "Unlimited":
        resolved = None
        reason = "unlimited"
    elif value == "Custom":
        resolved = parse_custom_stroke_count(custom_value)
        reason = "custom"
    elif value == "Auto":
        if time_budget_mode in ("Manual", "Unlimited", "Unlimited / Accuracy"):
            resolved = None
            reason = "manual-auto"
        else:
            resolved = _auto_count_from_time(effective_time_seconds, speed, drawing_mode, preview=preview)
            reason = "time-budget-auto"
    else:
        resolved = int(value)
        reason = "explicit"
    return resolved, {
        "target_stroke_count": source,
        "target_stroke_count_resolved": resolved,
        "target_stroke_count_reason": reason,
        "time_budget_mode": time_budget_mode,
        "time_budget_seconds": int(effective_time_seconds),
        "time_budget_active": time_budget_mode not in ("Manual", "Unlimited", "Unlimited / Accuracy"),
    }


def _path_len(path: Sequence[Point]) -> float:
    if len(path) < 2:
        return 0.0
    return sum(math.hypot(float(b[0] - a[0]), float(b[1] - a[1])) for a, b in zip(path, path[1:]))


def _importance_score(path: Sequence[Point], serial: int, *, prioritize_structure: bool = False) -> float:
    # Long paths are usually large visible shapes. Single-point details still get
    # a small score so a low cap keeps some dots instead of only outlines.
    length=_path_len(path)
    score=length + (2.5 if len(path) == 1 else 0.0)
    if prioritize_structure and path:
        xs=[float(p[0]) for p in path];ys=[float(p[1]) for p in path]
        span=math.hypot(max(xs)-min(xs),max(ys)-min(ys))
        closed=(len(path)>=4 and math.hypot(float(path[0][0]-path[-1][0]),float(path[0][1]-path[-1][1]))<=3.0)
        # v1.0.77: a tight real-time budget should preserve recognizable
        # structure before micro-detail. Large/closed contours receive a strong
        # deterministic bonus while isolated dots remain low priority.
        score += span*(1.65 if closed else .75)
        if closed:score += length*.30
        if len(path)==1:score *= .35
    return score - serial * 1e-9


def apply_target_path_cap(groups: Sequence[Sequence[Path]], cap: int | None, *, prioritize_structure: bool = False) -> tuple[list[list[Path]], dict]:
    """Keep the most visually important paths while preserving colour order.

    The returned groups are stable within each colour.  This works as a final
    execution-layer cap for both Smart paths and Shape paths.
    """
    normalized: list[list[Path]] = [[tuple(path) for path in paths if path] for paths in groups]
    before = sum(len(paths) for paths in normalized)
    if cap is None or before <= int(cap):
        return normalized, {"target_before_paths": before, "target_after_paths": before, "target_skipped_paths": 0, "structure_priority": bool(prioritize_structure)}
    cap = max(0, int(cap))
    entries: list[tuple[int, int, float, Path]] = []
    serial = 0
    for color_index, paths in enumerate(normalized):
        for path in paths:
            entries.append((color_index, serial, _importance_score(path, serial, prioritize_structure=prioritize_structure), path))
            serial += 1
    keep = heapq.nsmallest(cap, entries, key=lambda item: (-item[2], item[1]))
    regrouped: list[list[Path]] = [[] for _ in normalized]
    for color_index, serial, _score, path in sorted(keep, key=lambda item: (item[0], item[1])):
        regrouped[color_index].append(path)
    after = sum(len(paths) for paths in regrouped)
    return regrouped, {"target_before_paths": before, "target_after_paths": after, "target_skipped_paths": before - after, "structure_priority": bool(prioritize_structure)}
