"""Extra Fast 2.0 execution policy.

The old Extra Fast preset mainly enabled conservative bucket fills.  v2 keeps
those safe outline+fill substitutions, but also makes the normal fallback path
much cheaper by allowing longer *lossless* serpentine scanline paths.  A
connector is still only permitted where adjacent same-colour runs overlap, so
speed comes from fewer mouse press/release boundaries rather than painting
across gaps.

This module does not alter colors or remove details.  Color choice remains the
responsibility of the Step 1-6 color/accuracy pipeline.
"""
from __future__ import annotations

from typing import Any, Sequence


def path_limits(options: dict[str, Any]) -> tuple[int, int, str]:
    """Return bounded continuous-path limits for Extra Fast 2.0.

    Short deadlines tolerate longer mouse-down paths because boundary overhead
    dominates.  Longer/unlimited runs keep slightly shorter paths for easier
    recovery while still exceeding the legacy 72-row/320-point limits.
    """
    active = bool(options.get('time_budget_active'))
    try:
        seconds = float(options.get('max_seconds', 180) or 180)
    except (TypeError, ValueError):
        seconds = 180.0
    if active and seconds <= 80:
        return 220, 900, 'critical-deadline'
    if active and seconds <= 150:
        return 180, 760, 'short-deadline'
    if active and seconds <= 300:
        return 140, 620, 'timed'
    return 110, 480, 'quality-speed'


def build_meta(groups: Sequence[Sequence], execution_groups: Sequence[Sequence] | None,
               options: dict[str, Any], *, fill_regions=()) -> dict[str, Any]:
    source_runs = sum(len(g) for g in groups)
    scanline_paths = source_runs if execution_groups is None else sum(len(g) for g in execution_groups)
    rows, points, policy = path_limits(options)
    fill_regions = list(fill_regions or ())
    fill_pixels = sum(max(0, int(r.get('area_pixels', 0) or 0)) for r in fill_regions if isinstance(r, dict))
    return {
        'enabled': True,
        'engine': 'Extra Fast 2.0 hybrid region renderer',
        'strategy': 'OUTLINE_FILL -> CONNECTED_SCANLINES -> DETAIL',
        'color_pipeline_preserved': True,
        'source_runs_after_fill': int(source_runs),
        'connected_scanline_paths': int(scanline_paths),
        'scanline_boundaries_removed': max(0, int(source_runs - scanline_paths)),
        'scanline_boundary_reduction_percent': round((max(0, source_runs-scanline_paths)/max(1,source_runs))*100.0, 3),
        'fill_regions': len(fill_regions),
        'fill_pixels': int(fill_pixels),
        'max_rows_per_path': int(rows),
        'max_points_per_path': int(points),
        'path_policy': policy,
        'connector_rule': 'adjacent same-colour overlap only',
        'detail_protection': 'color/importance pipeline unchanged; no cross-gap shortcuts',
    }
