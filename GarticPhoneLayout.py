"""Reference geometry for the current Gartic Phone drawing layout.

This module never sends input and never guesses click positions.  It only
validates user-selected canvas geometry and documents the observed palette/tool
layout so calibration can give better guidance.
"""
from __future__ import annotations

REFERENCE_SCREEN_SIZE = (1920, 1080)
REFERENCE_CANVAS_BOX = (479, 319, 1461, 868)  # right/bottom exclusive
REFERENCE_CANVAS_SIZE = (982, 549)
REFERENCE_CANVAS_ASPECT = REFERENCE_CANVAS_SIZE[0] / REFERENCE_CANVAS_SIZE[1]
PALETTE_COLUMNS = 6
PALETTE_ROWS = 12
PALETTE_COLOR_COUNT = PALETTE_COLUMNS * PALETTE_ROWS

# Observed tool layout, described semantically only. Image Draw Bot still requires
# anchored user calibration before any native click is allowed.
TOOL_GRID = (
    ("Brush", "Eraser"),
    ("Rectangle outline", "Circle outline"),
    ("Filled rectangle", "Filled circle"),
    ("Line", "Fill"),
    ("Undo", "Redo"),
)


def assess_canvas_size(width: int, height: int) -> dict:
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        return {"likely": False, "aspect": 0.0, "reference_aspect": REFERENCE_CANVAS_ASPECT,
                "relative_error": 1.0, "confidence": 0.0}
    aspect = width / height
    relative_error = abs(aspect - REFERENCE_CANVAS_ASPECT) / REFERENCE_CANVAS_ASPECT
    # Responsive/browser scaling should preserve the canvas aspect. Keep this a
    # warning-only heuristic because themes and future Gartic layouts may change.
    confidence = max(0.0, min(1.0, 1.0 - relative_error / 0.18))
    return {
        "likely": relative_error <= 0.12,
        "aspect": aspect,
        "reference_aspect": REFERENCE_CANVAS_ASPECT,
        "relative_error": relative_error,
        "confidence": confidence,
    }
