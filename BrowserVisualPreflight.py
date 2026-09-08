"""Read-only visual preflight for supported browser drawing profiles.

v1.0.72 verifies that the browser still shows the same drawable canvas and a
representative set of calibrated palette swatches immediately before drawing.
It never emits mouse or keyboard input.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt
from typing import Iterable, Sequence

from BrowserAutoCalibration import SUPPORTED_BROWSER_PROFILES, detect_browser_setup, detect_browser_canvas


@dataclass(frozen=True)
class BrowserVisualPreflightResult:
    passed: bool
    profile_key: str
    confidence: float
    canvas_ok: bool
    palette_verified: int
    palette_tested: int
    max_palette_error: float
    reasons: tuple[str, ...]
    detected_canvas: tuple[int, int, int, int] | None

    @property
    def reason(self) -> str:
        return '; '.join(self.reasons) if self.reasons else 'visual preflight passed'


def _rect(value: Sequence[int], label: str) -> tuple[int, int, int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        raise ValueError(f'{label} rectangle is unavailable.')
    l, t, r, b = map(int, value)
    if r <= l or b <= t:
        raise ValueError(f'{label} rectangle is invalid.')
    return l, t, r, b


def _distance(a, b) -> float:
    return sqrt(sum((int(a[i]) - int(b[i])) ** 2 for i in range(3)))


def _sample_indices(count: int, max_samples: int = 6) -> tuple[int, ...]:
    count = max(0, int(count))
    max_samples = max(1, int(max_samples))
    if count <= max_samples:
        return tuple(range(count))
    # Evenly distribute checks across the palette so one color group/row cannot
    # accidentally make the whole preflight pass.
    raw = [round(i * (count - 1) / (max_samples - 1)) for i in range(max_samples)]
    result = []
    for index in raw:
        index = int(index)
        if index not in result:
            result.append(index)
    return tuple(result)


def _best_nearby_error(image, x: int, y: int, expected, *, radius: int = 2) -> float:
    w, h = image.size
    best = float('inf')
    for yy in range(max(0, y-radius), min(h, y+radius+1)):
        for xx in range(max(0, x-radius), min(w, x+radius+1)):
            best = min(best, _distance(image.getpixel((xx, yy))[:3], expected))
    return best


def _canvas_shift(a, b) -> int:
    if a is None or b is None:
        return 10**9
    return max(abs(int(x)-int(y)) for x, y in zip(a, b))


def verify_browser_visual_preflight(
    profile_key: str,
    target_metadata: dict,
    expected_canvas_box: Sequence[int],
    palette_entries: Iterable[tuple[Sequence[int], Sequence[int]]],
    *,
    screenshot=None,
    require_palette: bool = True,
    canvas_tolerance_px: int = 7,
    palette_tolerance: float = 42.0,
    max_palette_samples: int = 6,
) -> BrowserVisualPreflightResult:
    """Verify visible canvas + representative palette colors without input.

    ``palette_entries`` contains ``((screen_x, screen_y), (r,g,b))`` pairs.
    The check tolerates one transient/selected-swatch mismatch when six or more
    swatches are sampled, but never accepts fewer than three verified swatches.
    """
    profile_key = str(profile_key or '').lower()
    if profile_key not in SUPPORTED_BROWSER_PROFILES:
        raise ValueError('Browser Visual Preflight is not available for this profile.')
    client = _rect(target_metadata.get('client_rect'), 'Browser client')
    expected_canvas = _rect(expected_canvas_box, 'Expected canvas')
    left, top, right, bottom = client

    if screenshot is None:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab(bbox=client, all_screens=True).convert('RGB')
    else:
        screenshot = screenshot.convert('RGB')
    expected_size = (right-left, bottom-top)
    if screenshot.size != expected_size:
        raise ValueError(f'Browser screenshot size changed during visual preflight ({screenshot.size} != {expected_size}).')

    reasons: list[str] = []
    try:
        detector=detect_browser_setup if require_palette else detect_browser_canvas
        detected = detector(profile_key, screenshot, screen_origin=(left, top))
        detected_canvas = detected.get('canvas_box')
        canvas_confidence = float(detected.get('canvas_confidence') or 0.0)
    except Exception as error:
        detected_canvas = None
        canvas_confidence = 0.0
        reasons.append(f'canvas/palette detector could not verify the page: {error}')

    shift = _canvas_shift(expected_canvas, detected_canvas)
    canvas_ok = detected_canvas is not None and canvas_confidence >= .68 and shift <= max(0, int(canvas_tolerance_px))
    if not canvas_ok:
        if detected_canvas is None:
            reasons.append('canvas was not visually detected')
        elif canvas_confidence < .68:
            reasons.append(f'canvas confidence too low ({canvas_confidence*100:.0f}%)')
        else:
            reasons.append(f'canvas moved/reflowed by {shift}px')

    entries = list(palette_entries) if require_palette else []
    indices = _sample_indices(len(entries), max_palette_samples)
    verified = 0
    errors: list[float] = []
    for index in indices:
        position, expected_rgb = entries[index]
        sx, sy = int(position[0]), int(position[1])
        lx, ly = sx-left, sy-top
        if not (0 <= lx < screenshot.size[0] and 0 <= ly < screenshot.size[1]):
            errors.append(float('inf'))
            continue
        error = _best_nearby_error(screenshot, lx, ly, tuple(map(int, expected_rgb[:3])), radius=2)
        errors.append(error)
        if error <= float(palette_tolerance):
            verified += 1

    tested = len(indices)
    required = tested if tested <= 4 else max(3, ceil(tested * .80))
    palette_ok = (tested >= 3 and verified >= required) if require_palette else True
    max_error = max((e for e in errors if e != float('inf')), default=float('inf'))
    if require_palette and tested < 3:
        reasons.append(f'only {tested} palette control points were available')
    elif not palette_ok:
        reasons.append(f'palette verification matched only {verified}/{tested} control swatches')

    canvas_score = max(0.0, min(1.0, canvas_confidence)) if canvas_ok else 0.0
    palette_score = verified / tested if tested else 0.0
    confidence = .55 * canvas_score + .45 * palette_score if require_palette else canvas_score
    passed = bool(canvas_ok and palette_ok)
    return BrowserVisualPreflightResult(
        passed=passed,
        profile_key=profile_key,
        confidence=float(confidence),
        canvas_ok=bool(canvas_ok),
        palette_verified=int(verified),
        palette_tested=int(tested),
        max_palette_error=float(max_error),
        reasons=tuple(reasons),
        detected_canvas=tuple(map(int, detected_canvas)) if detected_canvas is not None else None,
    )
