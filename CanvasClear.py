"""Automatic target-canvas clearing for Image Draw Bot v1.0.114.

The module is deliberately deterministic and profile-aware.  It never guesses a
native UI coordinate: browser/game Clear, Brush and Eraser controls must come
from the existing anchored application-tool calibration.  Microsoft Paint uses
its document-level Select All/Delete shortcut when a keyboard backend is
available.  Eraser sweep is a bounded fallback that stays inside CanvasGuard.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

CLEAR_MODES = ("Off", "Before full drawing")


@dataclass(frozen=True)
class ClearStrategy:
    strategy: str
    reason: str = ""
    estimated_seconds: float = 0.0

    @property
    def available(self) -> bool:
        return self.strategy not in ("off", "unavailable")

    def as_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "reason": self.reason,
            "estimated_seconds": float(self.estimated_seconds),
            "available": bool(self.available),
        }


def validate_clear_mode(value: str) -> str:
    value = str(value or "Off")
    if value not in CLEAR_MODES:
        raise ValueError("Choose a valid automatic canvas-clear mode.")
    return value


def eraser_row_spacing(brush_px: int | float) -> int:
    """Overlap adjacent Eraser passes so narrow strips are not left behind."""
    try:
        brush = max(1.0, float(brush_px))
    except (TypeError, ValueError):
        brush = 3.0
    return max(1, int(math.floor(brush * 0.72)))


def estimate_eraser_sweep_seconds(width: int, height: int, brush_px: int | float) -> float:
    width, height = max(1, int(width)), max(1, int(height))
    rows = max(1, int(math.ceil(height / eraser_row_spacing(brush_px))))
    # Conservative UI/runtime estimate.  It is not used as a safety guarantee;
    # it only lets the existing time estimator account for the optional prelude.
    return max(1.0, rows * (0.025 + width / 18000.0))


def resolve_clear_strategy(*, paint_profile: bool, tools: dict | None = None,
                           keyboard_available: bool = True,
                           canvas_size: tuple[int, int] | None = None,
                           brush_px: int | float = 3) -> ClearStrategy:
    """Choose a safe clear method without inventing screen positions.

    Priority:
      1. Microsoft Paint Select All -> Delete -> Esc.
      2. User-calibrated one-click Clear canvas control.
      3. User-calibrated Eraser + Brush sweep fallback.
    """
    if paint_profile:
        if keyboard_available:
            return ClearStrategy("paint-shortcut", "Microsoft Paint Select All/Delete", 0.8)
        return ClearStrategy("unavailable", "Microsoft Paint automatic clear needs the keyboard backend.")

    tools = dict(tools or {})
    if tools.get("Clear") is not None:
        return ClearStrategy("native-clear", "Calibrated Clear canvas control", 0.8)
    if tools.get("Eraser") is not None and tools.get("Brush") is not None:
        w, h = canvas_size or (640, 400)
        return ClearStrategy(
            "eraser-sweep",
            "Calibrated Eraser sweep with Brush restore",
            estimate_eraser_sweep_seconds(w, h, brush_px),
        )
    return ClearStrategy(
        "unavailable",
        "Calibrate the app's Clear canvas button, or calibrate both Brush and Eraser for the sweep fallback.",
    )
