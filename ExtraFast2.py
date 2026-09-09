"""Extra Fast 2.0 execution policy.

The old Extra Fast preset mainly enabled conservative bucket fills. v2 keeps
those safe outline+fill substitutions, but also makes the normal fallback path
much cheaper by allowing longer *lossless* serpentine scanline paths. A
connector is still only permitted where adjacent same-colour runs overlap, so
speed comes from fewer mouse press/release boundaries rather than painting
across gaps.

The adaptive path policy added after the v1.0.133 review evaluates several
bounded continuous-path limits with Draw Studio's calibrated hybrid cost model.
It can therefore use longer same-colour paths where they are actually cheaper,
while retaining the previous plan whenever cost would increase. Horizontal and
vertical runs are evaluated independently; no diagonal connector is invented.

This module does not alter colors or remove details. Color choice remains the
responsibility of the Step 1-6 color/accuracy pipeline.
"""
from __future__ import annotations

from typing import Any, Sequence
import math


def path_limits(options: dict[str, Any]) -> tuple[int, int, str]:
    """Return bounded continuous-path limits for Extra Fast 2.0.

    Short deadlines tolerate longer mouse-down paths because boundary overhead
    dominates. Longer/unlimited runs keep slightly shorter paths for easier
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


def _candidate_limits(rows: int, points: int, policy: str) -> tuple[tuple[int, int], ...]:
    """Return a tiny bounded search space for safe continuous-path lengths.

    These are execution limits, not simplification levels. Every candidate uses
    the same source runs and the same overlap-only connector rule. The cost
    model chooses among them later and can always retain the baseline.
    """
    presets = {
        'critical-deadline': ((220,900),(320,1300)),
        'short-deadline': ((180,760),(260,1100)),
        'timed': ((140,620),(210,900)),
        'quality-speed': ((110,480),(160,720),(220,960)),
    }
    requested=((max(1,int(rows)),max(2,int(points))),)+tuple(presets.get(policy,()))
    out=[]
    for item in requested:
        normalized=(max(1,min(360,int(item[0]))),max(2,min(1400,int(item[1]))))
        if normalized not in out:
            out.append(normalized)
    return tuple(out)


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
        'adaptive_path_policy': 'cost-selected bounded path lengths; baseline retained on regression',
    }


def _axis_candidate(group, edge_n, rows, points, cancelled):
    """Build one lossless candidate for both axis-aligned run directions."""
    from ContinuousPaths import _horizontal_paths, _segment_path
    candidate=[_segment_path(s) for s in group[:edge_n]]
    horizontal=[];vertical=[];other=[]
    for x0,y0,x1,y1 in group[edge_n:]:
        if cancelled():raise InterruptedError()
        if y0==y1:
            horizontal.append((x0,y0,x1,y1))
        elif x0==x1:
            # Reuse the proven horizontal overlap planner by transposing axes.
            vertical.append((y0,x0,y1,x1))
        else:
            other.append(_segment_path((x0,y0,x1,y1)))
    candidate+=_horizontal_paths(horizontal,cancelled,max_rows_per_path=rows,max_points_per_path=points)
    joined_vertical=_horizontal_paths(vertical,cancelled,max_rows_per_path=rows,max_points_per_path=points)
    candidate+=[tuple((y,x) for x,y in path) for path in joined_vertical]
    candidate+=other
    return candidate,len(horizontal),len(vertical),len(joined_vertical)


def build_fast_paths(groups, options, *, portrait_edge_count=None, cancelled=lambda:False):
    """Choose the cheapest bounded lossless path plan per colour group.

    The legacy baseline is always built first. Extra Fast then evaluates a very
    small set of longer overlap-safe path limits. Both horizontal and vertical
    runs may benefit, but candidate plans are accepted only when they do not add
    execution paths and the calibrated intrinsic cost does not increase.

    Travel remains excluded because the downstream path-order optimizer owns
    pen-up ordering. Protected portrait edges stay at the front unchanged.
    """
    from ContinuousPaths import build_execution_paths
    from HybridCostModel import build_cost_model
    rows, points, policy = path_limits(options)
    limits=_candidate_limits(rows,points,policy)
    baseline = build_execution_paths(groups, enabled=True, portrait_edge_count=portrait_edge_count,
                                     max_rows_per_path=rows, max_points_per_path=points, cancelled=cancelled)
    model = build_cost_model(options)
    improved=[]
    vertical_runs=0;vertical_paths=0;vertical_colors=0
    horizontal_runs=0;horizontal_colors=0;adaptive_colors=0
    cost_before=0.0;cost_after=0.0
    selected_limits={}
    for index, group in enumerate(groups):
        if cancelled():raise InterruptedError()
        group=list(group)
        edge_n=max(0,min(len(group),int(portrait_edge_count))) if index==0 and portrait_edge_count is not None else 0
        original=list(baseline[index])
        before=sum(model.path_seconds(path) for path in original)
        best=original;best_cost=before;best_limit=(rows,points)
        best_h=best_v=best_vpaths=0
        for candidate_rows,candidate_points in limits:
            if cancelled():raise InterruptedError()
            candidate,h_runs,v_runs,v_paths=_axis_candidate(
                group,edge_n,candidate_rows,candidate_points,cancelled)
            after=sum(model.path_seconds(path) for path in candidate)
            # Extra Fast is boundary-oriented: do not accept more mouse-down
            # paths even when a synthetic cost estimate happens to prefer them.
            if len(candidate)>len(best):
                continue
            strictly_better=after < best_cost-1e-9
            equal_cost_fewer_paths=len(candidate)<len(best) and after<=best_cost+1e-9
            if strictly_better or equal_cost_fewer_paths:
                best=candidate;best_cost=after;best_limit=(candidate_rows,candidate_points)
                best_h,best_v,best_vpaths=h_runs,v_runs,v_paths
        improved.append(best)
        cost_before+=before;cost_after+=best_cost
        selected_limits[best_limit]=selected_limits.get(best_limit,0)+1
        if best is not original:
            adaptive_colors+=1
            if best_v:
                vertical_colors+=1;vertical_runs+=best_v;vertical_paths+=best_vpaths
            if best_h and best_limit!=(rows,points):
                horizontal_colors+=1;horizontal_runs+=best_h
    dominant_limit=max(selected_limits.items(),key=lambda item:(item[1],item[0]))[0] if selected_limits else (rows,points)
    return improved,dict(
        path_policy=policy,
        vertical_runs_joined=vertical_runs,
        vertical_paths=vertical_paths,
        vertical_colors_improved=vertical_colors,
        horizontal_runs_rebatched=horizontal_runs,
        horizontal_colors_improved=horizontal_colors,
        adaptive_colors_improved=adaptive_colors,
        intrinsic_cost_before_seconds=round(cost_before,6),
        intrinsic_cost_after_seconds=round(cost_after,6),
        intrinsic_cost_saved_seconds=round(max(0.0,cost_before-cost_after),6),
        candidate_path_limits=[list(item) for item in limits],
        dominant_selected_path_limit=list(dominant_limit),
        selected_path_limit_histogram={f'{r}x{p}':count for (r,p),count in sorted(selected_limits.items())},
        cost_scope='all color groups; excludes downstream travel ordering',
        safety_rule='same source runs; overlap-only axis connectors; no added path count; baseline on regression')
