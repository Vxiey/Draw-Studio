"""Local browser layout cache for Draw Studio v1.0.76.

The cache stores only deterministic layout/calibration metadata: profile key,
client size, DPI, a geometry-derived browser zoom/layout signature, canvas
coordinates and palette swatches. It never stores screenshots, source images,
URLs, telemetry or mouse input.

A cache hit is deliberately read-only. The current browser is sampled at a few
saved palette control points. Only after those samples match is the cached
canvas/palette restored. The normal Browser Visual Preflight still runs before
real drawing, so this is a setup speed-up rather than a safety bypass.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Iterable, Sequence

from CalibrationAnchors import make_anchor
from Colors import save_calibration
from RuntimePaths import atomic_write_text, data_dir
from ProfileStorage import profile_layout_cache_file

CACHE_FILE = data_dir() / 'layout-fingerprints-v2.json'
CACHE_VERSION = 2
MAX_PER_PROFILE = 8
MAX_TOTAL = 32


def _rect(value: Sequence[int], label: str = 'rectangle') -> tuple[int, int, int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        raise ValueError(f'{label} is unavailable.')
    l, t, r, b = map(int, value)
    if r <= l or b <= t:
        raise ValueError(f'{label} is invalid.')
    return l, t, r, b


def _rgb(value) -> tuple[int, int, int]:
    if not isinstance(value, (tuple, list)) or len(value) < 3:
        raise ValueError('RGB value is invalid.')
    result = tuple(max(0, min(255, int(v))) for v in value[:3])
    return result


def _distance(a, b) -> float:
    return math.sqrt(sum((int(a[i]) - int(b[i])) ** 2 for i in range(3)))


def _palette_spacing(points: Sequence[Sequence[int]]) -> float:
    pts = [(int(p[0]), int(p[1])) for p in points]
    if len(pts) < 2:
        return 0.0
    distances = []
    for a, b in zip(pts, pts[1:]):
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        if 2 <= d <= 250:
            distances.append(d)
    if not distances:
        return 0.0
    distances.sort()
    return float(distances[len(distances)//2])


def zoom_signature(client_rect: Sequence[int], canvas_box: Sequence[int], palette_positions: Sequence[Sequence[int]]) -> tuple[str, float]:
    """Return (stable signature, scale hint) inferred from browser geometry.

    Chrome does not expose its page-zoom percentage through the Win32 target
    metadata used by Draw Studio. We therefore persist a deterministic geometry
    signature that changes when page zoom/reflow changes, plus a normalized
    scale hint based on canvas width and palette spacing.
    """
    cl, ct, cr, cb = _rect(client_rect, 'client rectangle')
    xl, yt, xr, yb = _rect(canvas_box, 'canvas rectangle')
    cw, ch = cr-cl, cb-ct
    rel_canvas = (xl-cl, yt-ct, xr-cl, yb-ct)
    rel_palette = [(int(x)-cl, int(y)-ct) for x, y in palette_positions]
    spacing = _palette_spacing(rel_palette)
    canvas_ratio = (xr-xl) / max(1.0, float(cw))
    spacing_ratio = spacing / max(1.0, float(cw))
    payload = {
        'client': [cw, ch],
        'canvas': [round(v / max(1.0, float(cw if i % 2 == 0 else ch)), 5) for i, v in enumerate(rel_canvas)],
        'palette_spacing_ratio': round(spacing_ratio, 6),
        'palette_count': len(rel_palette),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()[:16]
    scale_hint = round((canvas_ratio * 0.75) + (spacing_ratio * 25.0), 4)
    return digest, scale_hint


def _empty_db() -> dict:
    return {'version': CACHE_VERSION, 'entries': []}


def load_cache(path: Path = CACHE_FILE) -> dict:
    try:
        raw = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(raw, dict) or int(raw.get('version', 0)) != CACHE_VERSION or not isinstance(raw.get('entries'), list):
            return _empty_db()
        entries = [entry for entry in raw['entries'] if isinstance(entry, dict)]
        return {'version': CACHE_VERSION, 'entries': entries[:MAX_TOTAL]}
    except (OSError, ValueError, TypeError):
        return _empty_db()


def save_cache(data: dict, path: Path = CACHE_FILE) -> None:
    entries = list(data.get('entries') or [])[:MAX_TOTAL]
    atomic_write_text(Path(path), json.dumps({'version': CACHE_VERSION, 'entries': entries}, ensure_ascii=False, indent=2))


def _relative_box(box, client):
    cl, ct, _cr, _cb = _rect(client, 'client rectangle')
    l, t, r, b = _rect(box, 'canvas rectangle')
    return [l-cl, t-ct, r-cl, b-ct]


def _absolute_box(rel, client):
    cl, ct, cr, cb = _rect(client, 'client rectangle')
    if not isinstance(rel, (tuple, list)) or len(rel) != 4:
        raise ValueError('Cached canvas rectangle is invalid.')
    l, t, r, b = [int(v) for v in rel]
    box = (cl+l, ct+t, cl+r, ct+b)
    if not (cl <= box[0] < box[2] <= cr and ct <= box[1] < box[3] <= cb):
        raise ValueError('Cached canvas is outside the current browser client.')
    return box


def record_layout(profile_key: str, target_metadata: dict, canvas_box: Sequence[int],
                  palette_entries: Iterable[dict], *, method: str = 'browser auto calibration',
                  path: Path | None = None) -> dict:
    client = _rect(target_metadata.get('client_rect'), 'client rectangle')
    dpi = target_metadata.get('dpi')
    cl, ct, cr, cb = client
    palette = []
    abs_positions = []
    for index, entry in enumerate(palette_entries):
        if not isinstance(entry, dict):
            continue
        pos = entry.get('position')
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            continue
        x, y = map(int, pos)
        rgb = _rgb(entry.get('rgb'))
        if not (cl <= x < cr and ct <= y < cb):
            continue
        abs_positions.append((x, y))
        palette.append({
            'name': str(entry.get('name') or f'Color {index+1}')[:80],
            'rel': [x-cl, y-ct],
            'rgb': list(rgb),
        })
    if len(palette) < 3:
        raise ValueError('At least three palette swatches are required for a layout fingerprint.')
    canvas = _rect(canvas_box, 'canvas rectangle')
    signature, zoom_hint = zoom_signature(client, canvas, abs_positions)
    now = time.time()
    entry = {
        'profile_key': str(profile_key or '').lower(),
        'client_size': [cr-cl, cb-ct],
        'dpi': int(dpi) if dpi is not None else None,
        'zoom_signature': signature,
        'browser_zoom_hint': zoom_hint,
        'canvas_rel': _relative_box(canvas, client),
        'palette': palette,
        'method': str(method)[:120],
        'saved_at': now,
        'last_used': now,
    }
    path = Path(path) if path is not None else profile_layout_cache_file(profile_key)
    db = load_cache(path)
    current = []
    for old in db['entries']:
        same = (
            old.get('profile_key') == entry['profile_key'] and
            old.get('client_size') == entry['client_size'] and
            old.get('dpi') == entry['dpi'] and
            old.get('zoom_signature') == signature
        )
        if not same:
            current.append(old)
    current.insert(0, entry)
    # Keep a bounded number per profile and globally.
    counts = {}
    kept = []
    for item in current:
        key = str(item.get('profile_key') or '')
        if counts.get(key, 0) >= MAX_PER_PROFILE:
            continue
        counts[key] = counts.get(key, 0) + 1
        kept.append(item)
        if len(kept) >= MAX_TOTAL:
            break
    save_cache({'version': CACHE_VERSION, 'entries': kept}, path)
    return dict(entry)


def record_from_calibration_file(profile_key: str, target_metadata: dict, canvas_box: Sequence[int],
                                 palette_path: Path, *, method: str = 'browser auto calibration',
                                 path: Path | None = None) -> dict:
    raw = json.loads(Path(palette_path).read_text(encoding='utf-8'))
    colors = raw.get('colors') if isinstance(raw, dict) else None
    if not isinstance(colors, list):
        raise ValueError('Saved palette calibration is unavailable for layout fingerprinting.')
    return record_layout(profile_key, target_metadata, canvas_box, colors, method=method, path=path)


def _sample_indices(count: int, limit: int = 6) -> tuple[int, ...]:
    if count <= 0:
        return ()
    if count <= limit:
        return tuple(range(count))
    values = [round(i*(count-1)/(limit-1)) for i in range(limit)]
    out = []
    for value in values:
        value = int(value)
        if value not in out:
            out.append(value)
    return tuple(out)


def _best_error(image, x: int, y: int, expected, radius: int = 2) -> float:
    w, h = image.size
    best = float('inf')
    for yy in range(max(0, y-radius), min(h, y+radius+1)):
        for xx in range(max(0, x-radius), min(w, x+radius+1)):
            best = min(best, _distance(image.getpixel((xx, yy))[:3], expected))
    return best


@dataclass(frozen=True)
class FingerprintRestoreResult:
    hit: bool
    profile_key: str
    canvas_box: tuple[int, int, int, int] | None
    palette_count: int
    confidence: float
    matched_swatches: int
    tested_swatches: int
    zoom_signature: str | None
    browser_zoom_hint: float | None
    reason: str

    def as_dict(self) -> dict:
        return {
            'hit': bool(self.hit), 'profile_key': self.profile_key,
            'canvas_box': self.canvas_box, 'palette_count': int(self.palette_count),
            'confidence': float(self.confidence), 'matched_swatches': int(self.matched_swatches),
            'tested_swatches': int(self.tested_swatches), 'zoom_signature': self.zoom_signature,
            'browser_zoom_hint': self.browser_zoom_hint, 'reason': self.reason,
        }


def try_restore(profile_key: str, target_metadata: dict, palette_path: Path, *, screenshot=None,
                tolerance: float = 42.0, path: Path | None = None) -> FingerprintRestoreResult:
    profile_key = str(profile_key or '').lower()
    path = Path(path) if path is not None else profile_layout_cache_file(profile_key)
    client = _rect(target_metadata.get('client_rect'), 'client rectangle')
    cl, ct, cr, cb = client
    size = [cr-cl, cb-ct]
    dpi = target_metadata.get('dpi')
    candidates = [entry for entry in load_cache(path)['entries']
                  if entry.get('profile_key') == profile_key and entry.get('client_size') == size
                  and (entry.get('dpi') is None or dpi is None or int(entry.get('dpi')) == int(dpi))]
    if not candidates:
        return FingerprintRestoreResult(False, profile_key, None, 0, 0.0, 0, 0, None, None, 'no matching client-size/DPI fingerprint')
    if screenshot is None:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab(bbox=client, all_screens=True).convert('RGB')
    else:
        screenshot = screenshot.convert('RGB')
    if screenshot.size != tuple(size):
        return FingerprintRestoreResult(False, profile_key, None, 0, 0.0, 0, 0, None, None, 'browser screenshot size changed')

    best = None
    for candidate in candidates:
        palette = candidate.get('palette') or []
        indices = _sample_indices(len(palette), 6)
        if len(indices) < 3:
            continue
        matched = 0
        errors = []
        for index in indices:
            item = palette[index]
            rel = item.get('rel') or []
            if len(rel) != 2:
                errors.append(float('inf')); continue
            x, y = map(int, rel)
            if not (0 <= x < screenshot.size[0] and 0 <= y < screenshot.size[1]):
                errors.append(float('inf')); continue
            error = _best_error(screenshot, x, y, _rgb(item.get('rgb')), radius=2)
            errors.append(error)
            if error <= tolerance:
                matched += 1
        required = len(indices) if len(indices) <= 4 else max(4, math.ceil(len(indices)*.80))
        confidence = matched / max(1, len(indices))
        score = (matched >= required, confidence, -max((e for e in errors if math.isfinite(e)), default=9999.0), float(candidate.get('last_used') or 0.0))
        if best is None or score > best[0]:
            best = (score, candidate, matched, len(indices), confidence)

    if best is None or not best[0][0]:
        return FingerprintRestoreResult(False, profile_key, None, 0, float(best[4] if best else 0.0), int(best[2] if best else 0), int(best[3] if best else 0), None, None, 'saved swatches did not match current browser layout')

    _score, candidate, matched, tested, confidence = best
    try:
        canvas = _absolute_box(candidate.get('canvas_rel'), client)
        palette = candidate.get('palette') or []
        positions = [(cl+int(item['rel'][0]), ct+int(item['rel'][1])) for item in palette]
        rgbs = [_rgb(item.get('rgb')) for item in palette]
        names = [str(item.get('name') or f'Color {i+1}') for i, item in enumerate(palette)]
        save_calibration(positions, rgbs, Path(palette_path), names=names, anchor=make_anchor(client), profile_key=profile_key, state='verified', verification={'method':'layout-fingerprint-screen-verification','confidence':float(confidence),'source':'profile-isolated-layout-cache'})
    except Exception as error:
        return FingerprintRestoreResult(False, profile_key, None, 0, confidence, matched, tested, None, None, f'cached layout could not be restored: {error}')

    # Touch last-used without changing the geometry signature.
    db = load_cache(path)
    for item in db['entries']:
        if item is candidate or (
            item.get('profile_key') == candidate.get('profile_key') and
            item.get('zoom_signature') == candidate.get('zoom_signature') and
            item.get('client_size') == candidate.get('client_size') and
            item.get('dpi') == candidate.get('dpi')
        ):
            item['last_used'] = time.time()
            break
    save_cache(db, path)
    return FingerprintRestoreResult(
        True, profile_key, canvas, len(candidate.get('palette') or []), float(confidence),
        matched, tested, str(candidate.get('zoom_signature') or ''),
        float(candidate.get('browser_zoom_hint') or 0.0),
        'layout fingerprint matched current palette control points',
    )
