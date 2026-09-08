"""Geometry-safe path optimizer for Draw Studio v1.0.37.

The optimizer only changes execution order/direction and may merge paths whose
endpoints are exactly identical. It never invents a connector across unpainted
space, so the visible geometry is preserved.
"""
from __future__ import annotations

import math
from typing import Sequence

Point = tuple[int, int]
Path = tuple[Point, ...]

STROKE_OPTIMIZER_MODES = ('Auto', 'Off', 'Travel only', 'Smart merge')


def validate_stroke_optimizer(mode: str) -> str:
    if mode not in STROKE_OPTIMIZER_MODES:
        raise ValueError('Choose a valid stroke optimizer mode.')
    return mode


def resolve_stroke_optimizer(mode: str, *, drawing_mode: str | None = None) -> str:
    validate_stroke_optimizer(mode)
    if mode != 'Auto':
        return mode
    if drawing_mode in ('Smart paths (recommended)', 'Shape paths'):
        return 'Smart merge'
    return 'Travel only'


def _distance(a: Point, b: Point) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _reverse(path: Path) -> Path:
    return tuple(reversed(path))


def pen_up_distance(paths: Sequence[Path]) -> float:
    total = 0.0
    previous = None
    for path in paths:
        if not path:
            continue
        if previous is not None:
            total += _distance(previous, path[0])
        previous = path[-1]
    return total


def _clean_path(path) -> Path:
    cleaned = []
    for point in path:
        p = (int(point[0]), int(point[1]))
        if not cleaned or cleaned[-1] != p:
            cleaned.append(p)
    return tuple(cleaned)


def _nearest_order(paths: Sequence[Path], *, speed: str = 'Balanced', allow_reverse: bool = True,
                   cancelled=lambda: False) -> list[Path]:
    """Adaptive bounded nearest-neighbour ordering.

    The window grows compared with the legacy optimizer, but remains bounded so
    thousands of paths do not turn planning into O(n^2) work.
    """
    remaining = [_clean_path(p) for p in paths if p]
    if len(remaining) < 3:
        return remaining
    if speed == 'Safe':
        window = 28
    elif speed == 'Fast':
        window = 160
    else:
        window = 96
    if len(remaining) > 12000:
        window = min(window, 72)
    elif len(remaining) < 500:
        window = min(len(remaining), max(window, 128))

    output: list[Path] = []
    first = remaining.pop(0)
    output.append(first)
    cursor = first[-1]

    while remaining:
        if cancelled():
            raise InterruptedError()
        limit = min(window, len(remaining))
        best_i = 0
        best_reverse = False
        best_cost = float('inf')
        # Search the next bounded slice. Removing selected items gradually slides
        # fresh candidates into the window while preserving a weak priority bias.
        for i in range(limit):
            path = remaining[i]
            d0 = _distance(cursor, path[0])
            d1 = _distance(cursor, path[-1]) if allow_reverse and len(path) > 1 else float('inf')
            reverse = d1 < d0
            cost = d1 if reverse else d0
            # Tiny stable priority penalty prevents distant low-priority paths from
            # constantly leapfrogging the beginning of the candidate window.
            cost += i * 1e-5
            if cost < best_cost:
                best_i, best_reverse, best_cost = i, reverse, cost
                if best_cost <= 1e-9:
                    break
        chosen = remaining.pop(best_i)
        if best_reverse:
            chosen = _reverse(chosen)
        output.append(chosen)
        cursor = chosen[-1]
    return output


def _merge_exact_neighbors(paths: Sequence[Path]) -> tuple[list[Path], int]:
    """Merge adjacent paths only when their endpoints are identical."""
    merged: list[Path] = []
    joins = 0
    for path in paths:
        path = _clean_path(path)
        if not path:
            continue
        if not merged:
            merged.append(path)
            continue
        previous = merged[-1]
        if previous[-1] == path[0]:
            merged[-1] = previous + path[1:]
            joins += 1
        elif len(path) > 1 and previous[-1] == path[-1]:
            rev = _reverse(path)
            merged[-1] = previous + rev[1:]
            joins += 1
        else:
            merged.append(path)
    return merged, joins



def _merge_exact_graph(paths: Sequence[Path], cancelled=lambda: False) -> tuple[list[Path], int]:
    """Build safe chains from paths that share exact endpoints anywhere in a group."""
    paths = [_clean_path(p) for p in paths if p]
    endpoint_map: dict[Point, list[int]] = {}
    for i, path in enumerate(paths):
        endpoint_map.setdefault(path[0], []).append(i)
        if path[-1] != path[0]:
            endpoint_map.setdefault(path[-1], []).append(i)
    used: set[int] = set()
    chains: list[Path] = []
    joins = 0

    for seed in range(len(paths)):
        if seed in used:
            continue
        if cancelled():
            raise InterruptedError()
        used.add(seed)
        chain = list(paths[seed])
        while True:
            if cancelled():
                raise InterruptedError()
            endpoint = chain[-1]
            candidate = None
            for idx in endpoint_map.get(endpoint, ()):
                if idx not in used:
                    candidate = idx
                    break
            if candidate is None:
                break
            path = paths[candidate]
            if path[0] == endpoint:
                oriented = path
            elif path[-1] == endpoint:
                oriented = _reverse(path)
            else:
                break
            used.add(candidate)
            chain.extend(oriented[1:])
            joins += 1
        chains.append(tuple(chain))
    return chains, joins

def optimize_path_group(paths: Sequence[Path], *, mode: str = 'Auto', drawing_mode: str | None = None,
                        speed: str = 'Balanced', allow_reverse: bool = True,
                        cancelled=lambda: False) -> tuple[list[Path], dict]:
    requested = mode
    effective = resolve_stroke_optimizer(mode, drawing_mode=drawing_mode)
    original = [_clean_path(p) for p in paths if p]
    before_distance = pen_up_distance(original)
    if effective == 'Off' or len(original) < 2:
        result = original
        joins = 0
    else:
        joins = 0
        working = original
        if effective == 'Smart merge':
            # Join exact shared endpoints globally before travel ordering. This can
            # collapse long segmented contours without drawing any new connector.
            working, joins = _merge_exact_graph(working, cancelled=cancelled)
        result = _nearest_order(working, speed=speed, allow_reverse=allow_reverse, cancelled=cancelled)
        if effective == 'Smart merge':
            # Ordering can place independent chains with a shared endpoint next to
            # each other; stitch that final exact boundary too.
            result, joins2 = _merge_exact_neighbors(result)
            joins += joins2
    after_distance = pen_up_distance(result)
    return result, {
        'stroke_optimizer_requested': requested,
        'stroke_optimizer_effective': effective,
        'optimizer_before_paths': len(original),
        'optimizer_after_paths': len(result),
        'optimizer_merged_paths': max(0, len(original) - len(result)),
        'optimizer_exact_joins': joins,
        'optimizer_pen_up_before': before_distance,
        'optimizer_pen_up_after': after_distance,
        'optimizer_travel_reduction': 0.0 if before_distance <= 0 else max(0.0, min(1.0, 1.0-after_distance/before_distance)),
    }


def optimize_execution_groups(groups: Sequence[Sequence[Path]], *, mode: str = 'Auto', drawing_mode: str | None = None,
                              speed: str = 'Balanced', phase_hints=None, cancelled=lambda: False):
    """Optimize every color group, preserving progressive phase boundaries."""
    optimized = []
    rebuilt_hints = [] if phase_hints is not None else None
    totals = {
        'optimizer_before_paths': 0, 'optimizer_after_paths': 0,
        'optimizer_merged_paths': 0, 'optimizer_exact_joins': 0,
        'optimizer_pen_up_before': 0.0, 'optimizer_pen_up_after': 0.0,
    }
    requested = mode
    effective = resolve_stroke_optimizer(mode, drawing_mode=drawing_mode)

    for gi, group in enumerate(groups):
        if cancelled():
            raise InterruptedError()
        group = list(group)
        hints = None
        if phase_hints is not None and gi < len(phase_hints) and len(phase_hints[gi]) == len(group):
            hints = list(phase_hints[gi])
        if hints:
            out = []
            out_hints = []
            # Keep phase order stable, optimize only within each contiguous phase.
            start = 0
            while start < len(group):
                phase = hints[start]
                end = start + 1
                while end < len(group) and hints[end] == phase:
                    end += 1
                part, meta = optimize_path_group(group[start:end], mode=mode, drawing_mode=drawing_mode,
                                                 speed=speed, cancelled=cancelled)
                out.extend(part); out_hints.extend([phase] * len(part))
                for key in totals:
                    totals[key] += meta[key]
                start = end
            optimized.append(out); rebuilt_hints.append(out_hints)
        else:
            out, meta = optimize_path_group(group, mode=mode, drawing_mode=drawing_mode,
                                            speed=speed, cancelled=cancelled)
            optimized.append(out)
            if rebuilt_hints is not None:
                rebuilt_hints.append([])
            for key in totals:
                totals[key] += meta[key]

    before = totals['optimizer_pen_up_before']; after = totals['optimizer_pen_up_after']
    totals.update({
        'stroke_optimizer_requested': requested,
        'stroke_optimizer_effective': effective,
        'optimizer_travel_reduction': 0.0 if before <= 0 else max(0.0, min(1.0, 1.0-after/before)),
    })
    return optimized, rebuilt_hints, totals
