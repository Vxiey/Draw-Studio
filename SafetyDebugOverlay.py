"""Safety debug overlay for Image Draw Bot v1.0.56.

This module is deterministic and UI-only. It does not decide whether a stroke is
safe; it records the already-resolved CanvasGuard/EdgeBehavior outcome and
renders a readable preview overlay that explains why a path was drawn, clipped,
skipped or edge-followed. No AI/ML/OCR is used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from PIL import Image, ImageDraw

Point = tuple[int, int]
Path = tuple[Point, ...]

# Keep one release preview small and deterministic. Full execution metadata keeps
# aggregate counters; the overlay samples representative paths so preview remains
# fast even for very large drawings.
MAX_DEBUG_EVENTS = 160
MAX_DEBUG_POINTS_PER_EVENT = 80

ACTION_COLORS = {
    'drawn': (84, 211, 159),
    'clipped': (240, 198, 107),
    'skipped': (255, 125, 144),
    'edge-follow': (115, 184, 255),
    'blocked': (255, 92, 122),
}
ACTION_LABELS = {
    'drawn': 'DRAWN',
    'clipped': 'CLIPPED',
    'skipped': 'SKIPPED',
    'edge-follow': 'EDGE-FOLLOW',
    'blocked': 'BLOCKED',
}


@dataclass(frozen=True)
class SafetyDebugEvent:
    path_index: int
    color_index: int
    action: str
    strategy: str
    reason: str
    original_points: tuple[Point, ...]
    output_subpaths: tuple[Path, ...] = field(default_factory=tuple)
    output_points: int = 0

    def as_dict(self) -> dict:
        return {
            'path_index': int(self.path_index),
            'color_index': int(self.color_index),
            'action': self.action,
            'strategy': self.strategy,
            'reason': self.reason,
            'original_points': self.original_points,
            'output_subpaths': self.output_subpaths,
            'output_points': int(self.output_points),
        }


def _round_point(point: Sequence[int | float]) -> Point:
    return (int(round(float(point[0]))), int(round(float(point[1]))))


def _limit_path(points: Sequence[Sequence[int | float]], limit: int = MAX_DEBUG_POINTS_PER_EVENT) -> tuple[Point, ...]:
    rounded = tuple(_round_point(p) for p in points)
    if len(rounded) <= limit:
        return rounded
    step = max(1, len(rounded) // limit)
    sampled = list(rounded[::step][:limit - 1])
    if rounded[-1] not in sampled:
        sampled.append(rounded[-1])
    return tuple(sampled)


def classify_edge_result(edge_result, raw_points: Sequence[Sequence[int | float]]) -> tuple[str, str]:
    """Return user-facing action/reason from an EdgeBehaviorResult."""
    strategy = str(getattr(edge_result, 'strategy', '') or '')
    subpaths = tuple(tuple(_round_point(p) for p in path) for path in getattr(edge_result, 'subpaths', ()) or ())
    original = tuple(_round_point(p) for p in raw_points)
    original_points = int(getattr(edge_result, 'original_points', len(original)) or len(original))
    output_points = int(getattr(edge_result, 'output_points', sum(len(p) for p in subpaths)) or 0)

    if strategy == 'hard_clip':
        same_points = output_points == original_points and len(subpaths) == 1 and subpaths[0] == original if subpaths and original else False
        if same_points:
            return 'drawn', 'All source points were already inside the brush-inset safe polygon.'
        return 'clipped', 'Stroke crossed or touched the brush-inset safe polygon and was mathematically clipped.'
    if strategy == 'hard_skip':
        return 'skipped', 'Hard Clip removed the whole stroke because it only existed in the unsafe edge band.'
    if strategy == 'adaptive_boundary':
        return 'edge-follow', 'Adaptive Clip projected a near-edge stroke onto the safe inset boundary.'
    if strategy == 'preserve_outline_boundary':
        return 'edge-follow', 'Preserve Outline projected a near-edge outline onto the safe inset boundary.'
    if strategy == 'safe_skip':
        return 'skipped', 'Stroke was too far outside the safe inset to project back without changing the drawing.'
    return 'skipped', f'Unhandled safety strategy {strategy!r}; stroke was not used in the safe preview.'


def make_debug_event(
    path_index: int,
    color_index: int,
    raw_points: Sequence[Sequence[int | float]],
    edge_result=None,
    *,
    exception: Exception | None = None,
) -> SafetyDebugEvent:
    original = _limit_path(raw_points)
    if exception is not None:
        return SafetyDebugEvent(
            path_index=path_index,
            color_index=color_index,
            action='blocked',
            strategy='source_outside_canvas',
            reason='CanvasGuard rejected at least one source point outside the selected canvas polygon.',
            original_points=original,
            output_subpaths=(),
            output_points=0,
        )
    action, reason = classify_edge_result(edge_result, raw_points)
    subpaths = tuple(_limit_path(path) for path in (getattr(edge_result, 'subpaths', ()) or ()))
    output_points = int(getattr(edge_result, 'output_points', sum(len(p) for p in subpaths)) or 0)
    return SafetyDebugEvent(
        path_index=path_index,
        color_index=color_index,
        action=action,
        strategy=str(getattr(edge_result, 'strategy', '') or ''),
        reason=reason,
        original_points=original,
        output_subpaths=subpaths,
        output_points=output_points,
    )


def add_debug_event(meta: dict, event: SafetyDebugEvent) -> None:
    counts = meta.setdefault('debug_counts', {'drawn': 0, 'clipped': 0, 'skipped': 0, 'edge-follow': 0, 'blocked': 0})
    counts[event.action] = int(counts.get(event.action, 0)) + 1
    # Also mirror common keys at top level for older status code and tests.
    meta[f'debug_{event.action.replace("-", "_")}'] = int(meta.get(f'debug_{event.action.replace("-", "_")}', 0)) + 1
    events = meta.setdefault('debug_events', [])
    if len(events) < MAX_DEBUG_EVENTS:
        events.append(event.as_dict())
    else:
        meta['debug_events_truncated'] = int(meta.get('debug_events_truncated', 0)) + 1


def summarize_debug(meta: dict) -> dict:
    counts = dict(meta.get('debug_counts') or {})
    for key in ('drawn', 'clipped', 'skipped', 'edge-follow', 'blocked'):
        counts[key] = int(counts.get(key, 0) or 0)
    return {
        'active': True,
        'drawn': counts['drawn'],
        'clipped': counts['clipped'],
        'skipped': counts['skipped'],
        'edge_follow': counts['edge-follow'],
        'blocked': counts['blocked'],
        'events_sampled': len(meta.get('debug_events') or ()),
        'events_truncated': int(meta.get('debug_events_truncated', 0) or 0),
    }


def _canvas_to_preview(point: Sequence[int | float], fitted: Sequence[int | float], preview_size: Sequence[int | float]) -> tuple[float, float]:
    fw, fh = max(1.0, float(fitted[0])), max(1.0, float(fitted[1]))
    pw, ph = max(1.0, float(preview_size[0])), max(1.0, float(preview_size[1]))
    return (float(point[0]) * pw / fw, float(point[1]) * ph / fh)


def _draw_polyline(draw: ImageDraw.ImageDraw, points: Sequence[Sequence[int | float]], fitted, preview_size, *, fill, width=2, dashed=False) -> None:
    mapped = [_canvas_to_preview(p, fitted, preview_size) for p in points]
    if len(mapped) == 1:
        x, y = mapped[0]
        r = max(2, width + 1)
        draw.ellipse((x - r, y - r, x + r, y + r), outline=fill, width=width)
        return
    if len(mapped) < 2:
        return
    for idx, (a, b) in enumerate(zip(mapped, mapped[1:])):
        if dashed and idx % 2:
            continue
        draw.line((a[0], a[1], b[0], b[1]), fill=fill, width=width)


def _draw_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, *, fill=(230, 237, 245), bg=(15, 20, 29)) -> int:
    width = min(920, max(30, len(text) * 6 + 10))
    draw.rectangle((x, y, x + width, y + 17), fill=bg)
    draw.text((x + 5, y + 3), text, fill=fill)
    return y + 19


def render_safety_debug_overlay(preview_size, safety_plan, palette_rgb, brush: int, cancelled=lambda: False) -> Image.Image:
    """Render a debug overlay showing per-path safety reasons.

    The overlay is intentionally separate from the normal Safety map. It draws:
      - faint raw path samples for skipped/blocked items
      - solid output paths for drawn/clipped/adaptive results
      - a concise legend and first few exact reasons
    """
    w, h = int(preview_size[0]), int(preview_size[1])
    base = Image.new('RGB', (max(1, w), max(1, h)), (12, 16, 24))
    draw = ImageDraw.Draw(base)
    meta = getattr(safety_plan, 'meta', {}) or {}
    guard_meta = meta.get('canvas_guard') or {}
    fitted = guard_meta.get('area') or (0, 0, w, h)
    fitted_size = (max(1, int(fitted[2])), max(1, int(fitted[3]))) if len(fitted) == 4 else preview_size

    # Safe polygon context.
    for key, color, width in (('polygon', (82, 100, 125), 1), ('safe_polygon', (98, 226, 146), 2)):
        poly = guard_meta.get(key) or ()
        mapped = []
        for p in poly:
            try:
                mapped.append(_canvas_to_preview(p, fitted_size, preview_size))
            except Exception:
                continue
        if len(mapped) >= 2:
            draw.line([coord for p in mapped + mapped[:1] for coord in p], fill=color, width=width)

    events = list(meta.get('debug_events') or ())
    for event in events:
        if cancelled():
            raise InterruptedError()
        action = str(event.get('action') or 'skipped')
        color = ACTION_COLORS.get(action, ACTION_COLORS['skipped'])
        raw = event.get('original_points') or ()
        outputs = event.get('output_subpaths') or ()
        if action in ('skipped', 'blocked'):
            _draw_polyline(draw, raw, fitted_size, preview_size, fill=color, width=max(1, min(3, int(brush))), dashed=True)
        else:
            # Draw a faint raw reference below the actual executable result for clipped paths.
            if action in ('clipped', 'edge-follow'):
                _draw_polyline(draw, raw, fitted_size, preview_size, fill=(64, 76, 94), width=1, dashed=True)
            for path in outputs:
                _draw_polyline(draw, path, fitted_size, preview_size, fill=color, width=max(1, min(5, int(brush))))

    counts = summarize_debug(meta)
    y = 8
    y = _draw_text(draw, 8, y, f"Safety debug: {getattr(safety_plan, 'mode', 'CanvasGuard')} · drawn {counts['drawn']} · clipped {counts['clipped']} · skipped {counts['skipped']} · edge-follow {counts['edge_follow']} · blocked {counts['blocked']}")
    legend = 'Legend: green=drawn · yellow=clipped · red dashed=skipped/blocked · blue=edge-follow · gray dashed=raw source reference'
    y = _draw_text(draw, 8, y, legend, fill=(190, 204, 220))
    if counts['events_truncated']:
        y = _draw_text(draw, 8, y, f"Debug overlay sampled {counts['events_sampled']} paths; {counts['events_truncated']} more hidden to keep preview fast.", fill=(240, 198, 107), bg=(39, 31, 17))
    # Show first several exact reasons, preferring non-drawn paths.
    interesting = [e for e in events if e.get('action') != 'drawn'] + [e for e in events if e.get('action') == 'drawn']
    for event in interesting[:5]:
        label = ACTION_LABELS.get(str(event.get('action')), str(event.get('action')).upper())
        reason = str(event.get('reason') or '')
        color = ACTION_COLORS.get(str(event.get('action')), (230, 237, 245))
        y = _draw_text(draw, 8, y, f"#{int(event.get('path_index', 0))}: {label} · {reason}", fill=color, bg=(16, 23, 34))
        if y > h - 28:
            break
    return base
