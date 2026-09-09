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
import math


def path_limits(options: dict[str, Any]) -> tuple[int, int, str]:
    """Return bounded continuous-path limits for Extra Fast 2.0.

    Short deadlines tolerate longer mouse-down paths because boundary overhead
    dominates.  Longer/unlimited runs keep slightly shorter paths for easier
    recovery while still exceeding the legacy 72-row/320-point limits.
    """
    active = bool(options.get('time_budget_active')) and not (
        options.get('unlimited_time') or options.get('time_budget_mode') in ('Unlimited','Unlimited / Accuracy'))
    try:
        seconds = float(options.get('max_seconds', 180) or 180)
    except (TypeError, ValueError, OverflowError):
        seconds = 180.0
    if not math.isfinite(seconds) or seconds <= 0:
        seconds=180.0
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


def build_fast_paths(groups, options, *, portrait_edge_count=None, cancelled=lambda:False):
    """Join both axis-aligned run directions without changing raster geometry.

    Horizontal and vertical runs are kept in separate sets so no diagonal
    connector is invented. Protected portrait edges remain at the front.
    Keep the old plan if joining vertical runs increases its intrinsic cost.
    Travel is excluded because the downstream optimizer owns path ordering.
    """
    from ContinuousPaths import build_execution_paths, _horizontal_paths, _segment_path
    from HybridCostModel import build_cost_model
    rows, points, policy = path_limits(options)
    baseline = build_execution_paths(groups, enabled=True, portrait_edge_count=portrait_edge_count,
                                     max_rows_per_path=rows, max_points_per_path=points, cancelled=cancelled)
    model = None
    improved=[];vertical_runs=0;vertical_paths=0;accepted_colors=0
    cost_before=0.0;cost_after=0.0
    for index, group in enumerate(groups):
        if cancelled():raise InterruptedError()
        edge_n=max(0,min(len(group),int(portrait_edge_count))) if index==0 and portrait_edge_count is not None else 0
        horizontal=[];vertical=[];other=[]
        for x0,y0,x1,y1 in group[edge_n:]:
            if cancelled():raise InterruptedError()
            if y0==y1:
                horizontal.append((x0,y0,x1,y1))
            elif x0==x1:
                vertical.append((y0,x0,y1,x1))
            else:
                other.append(_segment_path((x0,y0,x1,y1)))
        original=baseline[index]
        if vertical:
            if model is None:
                model = build_cost_model(options)
            candidate=[_segment_path(s) for s in group[:edge_n]]
            candidate+=_horizontal_paths(horizontal,cancelled,max_rows_per_path=rows,max_points_per_path=points)
            joined=_horizontal_paths(vertical,cancelled,max_rows_per_path=rows,max_points_per_path=points)
            candidate+=[tuple((y,x) for x,y in path) for path in joined]
            candidate+=other
            before=sum(model.path_seconds(path) for path in original)
            after=sum(model.path_seconds(path) for path in candidate)
            if len(candidate)<len(original) and after<=before+1e-9:
                improved.append(candidate);accepted_colors+=1
                vertical_runs+=len(vertical);vertical_paths+=len(joined)
                cost_before+=before;cost_after+=after
                continue
            cost_before+=before;cost_after+=before
        improved.append(original)
    return improved,dict(path_policy=policy,vertical_runs_joined=vertical_runs,
                         vertical_paths=vertical_paths,vertical_colors_improved=accepted_colors,
                         intrinsic_cost_before_seconds=round(cost_before,6),
                         intrinsic_cost_after_seconds=round(cost_after,6),
                         cost_scope='groups containing vertical runs; excludes downstream travel ordering')
