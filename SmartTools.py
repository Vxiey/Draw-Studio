"""Plan-level drawing-tool choice for Image Draw Bot v1.0.7."""
from __future__ import annotations

TOOL_STRATEGIES = ("Auto", "Precision first", "Speed first", "Respect selected")


def validate_tool_strategy(value: str) -> str:
    if value not in TOOL_STRATEGIES:
        raise ValueError("Tool strategy must be Auto, Precision first, Speed first or Respect selected.")
    return value


def choose_paint_tool(selected: str, strategy: str, calibration: dict | None, *, portrait: bool, brush_px: int) -> str:
    """Choose a concrete Paint tool without inventing uncalibrated controls."""
    validate_tool_strategy(strategy)
    if selected != "Auto (recommended)" or strategy == "Respect selected":
        return selected
    data = calibration or {}; tools = data.get("tools", {}) if isinstance(data, dict) else {}
    pencil_ready = tools.get("Pencil") is not None
    brush_ready = data.get("opacity_100") is not None and data.get("brush_menu") is not None and data.get("brush_preset") is not None
    if strategy == "Precision first":
        if pencil_ready: return "Pencil"
        if brush_ready: return "Brush"
    elif strategy == "Speed first":
        if brush_ready: return "Brush"
        if pencil_ready: return "Pencil"
    else:
        # Portrait/small brush work benefits from Pencil.  Standard large-area
        # palette rendering can use a calibrated solid Brush to reduce event load.
        if portrait or int(brush_px) <= 1:
            if pencil_ready: return "Pencil"
            if brush_ready: return "Brush"
        else:
            if brush_ready: return "Brush"
            if pencil_ready: return "Pencil"
    return selected
