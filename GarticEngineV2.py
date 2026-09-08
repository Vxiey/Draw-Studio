"""Gartic Phone Engine v2 planning and layout helpers.

Pure deterministic code only: no native mouse input, no browser access and no
network calls.  The helpers are intentionally conservative so failed detection
returns a low-confidence result instead of guessing clickable coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from GarticPhoneLayout import REFERENCE_CANVAS_ASPECT

Point = tuple[int, int]
Path = tuple[Point, ...]
Box = tuple[int, int, int, int]


@dataclass(frozen=True)
class CanvasDetection:
    found: bool
    box: Box | None
    confidence: float
    aspect: float
    white_score: float
    frame_score: float
    reason: str

    def as_options(self) -> dict:
        return {
            "found": self.found,
            "box": self.box,
            "confidence": self.confidence,
            "aspect": self.aspect,
            "white_score": self.white_score,
            "frame_score": self.frame_score,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GarticRuntimeProfile:
    seconds_left: int | None
    max_colors: int
    max_paths: int
    stroke_step_px: float
    precision: str
    adaptive_detail: str
    color_order: str
    reason: str

    def as_options(self) -> dict:
        return {
            "seconds_left": self.seconds_left,
            "max_colors": self.max_colors,
            "max_paths": self.max_paths,
            "stroke_step_px": self.stroke_step_px,
            "precision": self.precision,
            "adaptive_detail": self.adaptive_detail,
            "color_order": self.color_order,
            "reason": self.reason,
        }


def _near_white(rgb) -> bool:
    r, g, b = map(int, rgb[:3])
    return r >= 242 and g >= 242 and b >= 242 and max(r, g, b) - min(r, g, b) <= 18


def _purple_frame(rgb) -> bool:
    r, g, b = map(int, rgb[:3])
    return b >= 95 and r >= 55 and g <= 100 and (b - g) >= 35


def _flood_largest_white(mask: list[bytearray], *, min_area: int) -> tuple[Box | None, int]:
    h = len(mask)
    w = len(mask[0]) if h else 0
    visited = [bytearray(w) for _ in range(h)]
    best_box: Box | None = None
    best_area = 0
    for sy in range(h):
        row = mask[sy]
        for sx in range(w):
            if not row[sx] or visited[sy][sx]:
                continue
            visited[sy][sx] = 1
            stack = [(sx, sy)]
            left = right = sx
            top = bottom = sy
            area = 0
            while stack:
                x, y = stack.pop()
                area += 1
                if x < left: left = x
                elif x > right: right = x
                if y < top: top = y
                elif y > bottom: bottom = y
                nx = x - 1
                if nx >= 0 and mask[y][nx] and not visited[y][nx]:
                    visited[y][nx] = 1; stack.append((nx, y))
                nx = x + 1
                if nx < w and mask[y][nx] and not visited[y][nx]:
                    visited[y][nx] = 1; stack.append((nx, y))
                ny = y - 1
                if ny >= 0 and mask[ny][x] and not visited[ny][x]:
                    visited[ny][x] = 1; stack.append((x, ny))
                ny = y + 1
                if ny < h and mask[ny][x] and not visited[ny][x]:
                    visited[ny][x] = 1; stack.append((x, ny))
            if area >= min_area and area > best_area:
                best_area = area
                best_box = (left, top, right + 1, bottom + 1)
    return best_box, best_area


def _frame_score(image, box: Box, pad: int = 7) -> float:
    image = image.convert('RGB')
    w, h = image.size
    left, top, right, bottom = box
    samples = []
    for x in range(max(0, left-pad), min(w, right+pad)):
        for y in (max(0, top-pad), min(h-1, bottom+pad-1)):
            samples.append(image.getpixel((x, y)))
    for y in range(max(0, top-pad), min(h, bottom+pad)):
        for x in (max(0, left-pad), min(w-1, right+pad-1)):
            samples.append(image.getpixel((x, y)))
    if not samples:
        return 0.0
    return sum(1 for rgb in samples if _purple_frame(rgb)) / len(samples)


def detect_gartic_canvas(image, *, downsample: int = 2, min_canvas_area_ratio: float = 0.08) -> CanvasDetection:
    """Detect the visible white Gartic canvas from a screenshot.

    The function never returns guessed coordinates when confidence is low. It is
    safe to use as guidance or to prefill a user confirmation step.
    """
    image = image.convert('RGB')
    w, h = image.size
    if w < 200 or h < 120:
        return CanvasDetection(False, None, 0.0, 0.0, 0.0, 0.0, 'image too small')
    step = max(1, int(downsample))
    sw, sh = (w + step - 1) // step, (h + step - 1) // step
    mask = [bytearray(sw) for _ in range(sh)]
    for yy in range(sh):
        y = min(h - 1, yy * step)
        for xx in range(sw):
            x = min(w - 1, xx * step)
            if _near_white(image.getpixel((x, y))):
                mask[yy][xx] = 1
    min_area = max(32, int(sw * sh * float(min_canvas_area_ratio)))
    small_box, white_area = _flood_largest_white(mask, min_area=min_area)
    if small_box is None:
        return CanvasDetection(False, None, 0.0, 0.0, 0.0, 0.0, 'no large white canvas region')
    l, t, r, b = small_box
    box = (l * step, t * step, min(w, r * step), min(h, b * step))
    bw, bh = box[2] - box[0], box[3] - box[1]
    if bw <= 0 or bh <= 0:
        return CanvasDetection(False, None, 0.0, 0.0, 0.0, 0.0, 'invalid canvas box')
    aspect = bw / bh
    aspect_score = max(0.0, 1.0 - abs(aspect - REFERENCE_CANVAS_ASPECT) / 0.25)
    white_score = min(1.0, white_area / max(1, (bw / step) * (bh / step)))
    frame = _frame_score(image, box)
    # Purple frame can be partly hidden by UI scaling/antialiasing, so aspect and
    # white solidity dominate. A strong frame simply pushes confidence higher.
    confidence = max(0.0, min(1.0, 0.52 * aspect_score + 0.33 * white_score + 0.15 * min(1.0, frame * 4)))
    found = confidence >= 0.70 and aspect_score >= 0.55 and white_score >= 0.70
    reason = 'gartic canvas matched' if found else 'candidate needs user confirmation'
    return CanvasDetection(found, box if found else None, confidence, aspect, white_score, frame, reason)


def choose_runtime_profile(seconds_left: int | None, *, canvas_size: tuple[int, int] | None = None,
                           requested_speed: str = 'Fast') -> GarticRuntimeProfile:
    """Return deterministic Gartic settings for normal/turbo/time-critical phases."""
    try:
        seconds = None if seconds_left is None else max(0, int(seconds_left))
    except (TypeError, ValueError):
        seconds = None
    speed = str(requested_speed or 'Fast')
    pixels = 0
    if canvas_size:
        try:
            pixels = max(0, int(canvas_size[0])) * max(0, int(canvas_size[1]))
        except Exception:
            pixels = 0
    if seconds is not None and seconds <= 20:
        return GarticRuntimeProfile(seconds, 4, 350, 24.0, 'Normal', 'Extreme simplify', 'dark-first', 'final seconds turbo')
    if seconds is not None and seconds <= 45:
        return GarticRuntimeProfile(seconds, 6, 650, 20.0, 'Normal', 'Strong simplify', 'dark-first', 'low time turbo')
    if pixels and pixels > 1_200_000:
        return GarticRuntimeProfile(seconds, 7, 850, 18.0, 'Normal', 'Strong simplify', 'dark-first', 'large canvas turbo')
    if speed == 'Safe':
        return GarticRuntimeProfile(seconds, 8, 1000, 12.0, 'High', 'Balanced', 'largest-first', 'safe quality')
    return GarticRuntimeProfile(seconds, 8, 1000, 16.0, 'Normal', 'Strong simplify', 'largest-first', 'default gartic turbo')


def _dist(a: Point, b: Point) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _clean(path: Sequence[Point]) -> Path:
    out: list[Point] = []
    for x, y in path:
        p = (int(x), int(y))
        if not out or out[-1] != p:
            out.append(p)
    return tuple(out)


def stroke_graph_order(paths: Sequence[Sequence[Point]], *, allow_reverse: bool = True,
                       window: int = 192, cancelled=lambda: False) -> tuple[list[Path], dict]:
    """Bounded nearest-neighbour StrokeGraph order for one color batch.

    It changes only order and direction. It never adds connector strokes, so the
    geometry remains safe for CanvasGuard and SafePolygon clipping.
    """
    remaining = [_clean(p) for p in paths if p]
    before = len(remaining)
    if before < 3:
        return remaining, {'stroke_graph': True, 'before_paths': before, 'after_paths': before,
                           'pen_up_before': 0.0, 'pen_up_after': 0.0, 'travel_reduction': 0.0}

    def pen_up(seq: Sequence[Path]) -> float:
        total = 0.0; prev = None
        for path in seq:
            if prev is not None:
                total += _dist(prev, path[0])
            prev = path[-1]
        return total

    before_dist = pen_up(remaining)
    out: list[Path] = []
    current = remaining.pop(0)
    out.append(current)
    cursor = current[-1]
    limit_window = max(8, min(int(window), 256))
    while remaining:
        if cancelled():
            raise InterruptedError()
        limit = min(limit_window, len(remaining))
        best_i = 0; best_rev = False; best = float('inf')
        for i in range(limit):
            path = remaining[i]
            d0 = _dist(cursor, path[0])
            d1 = _dist(cursor, path[-1]) if allow_reverse and len(path) > 1 else float('inf')
            if d1 < d0:
                d = d1; rev = True
            else:
                d = d0; rev = False
            d += i * 1e-5
            if d < best:
                best_i, best_rev, best = i, rev, d
        chosen = remaining.pop(best_i)
        if best_rev:
            chosen = tuple(reversed(chosen))
        out.append(chosen)
        cursor = chosen[-1]
    after_dist = pen_up(out)
    return out, {
        'stroke_graph': True,
        'before_paths': before,
        'after_paths': len(out),
        'pen_up_before': before_dist,
        'pen_up_after': after_dist,
        'travel_reduction': 0.0 if before_dist <= 0 else max(0.0, min(1.0, 1.0 - after_dist / before_dist)),
        'allow_reverse': bool(allow_reverse),
        'window': limit_window,
    }
