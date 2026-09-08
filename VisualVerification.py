"""Fast visual verification after each color batch (v1.0.43).

This module is pure image analysis. It never reads the screen or sends input by
itself; the guarded execution layer supplies already-captured canvas snapshots.
The goal is quick fault detection, not pixel-perfect reconstruction.
"""
from __future__ import annotations

from math import hypot
from typing import Iterable, Sequence

VISUAL_VERIFICATION_MODES = ("Auto", "Off", "Fast", "Balanced", "Strict")


def validate_visual_verification(value: str) -> str:
    if value not in VISUAL_VERIFICATION_MODES:
        raise ValueError("Visual verification must be Auto, Off, Fast, Balanced or Strict.")
    return value


def resolve_visual_verification(value: str, *, paint_profile: bool = True, dry_run: bool = False, test: bool = False) -> str:
    validate_visual_verification(value)
    if dry_run or test or not paint_profile:
        return "Off" if value == "Auto" else value
    if value == "Auto":
        return "Balanced"
    return value


def rgb_error(a: Sequence[int], b: Sequence[int]) -> int:
    return max(abs(int(a[i]) - int(b[i])) for i in range(3))


def _mode_config(mode: str) -> dict:
    mode = validate_visual_verification(mode)
    if mode == "Fast":
        return dict(tolerance=72, min_match=0.45, max_outside=0.060, max_outside_samples=220, sample_limit=80)
    if mode == "Strict":
        return dict(tolerance=46, min_match=0.68, max_outside=0.018, max_outside_samples=55, sample_limit=180)
    # Balanced / Auto after resolution.
    return dict(tolerance=58, min_match=0.55, max_outside=0.035, max_outside_samples=120, sample_limit=130)


def _line_points(a, b, steps=None):
    x0, y0 = map(float, a[:2]); x1, y1 = map(float, b[:2])
    dist = max(abs(x1 - x0), abs(y1 - y0), 1.0)
    n = int(steps if steps is not None else max(2, min(16, round(dist) + 1)))
    if n <= 1:
        return [(round(x0), round(y0))]
    return [(round(x0 + (x1 - x0) * i / (n - 1)), round(y0 + (y1 - y0) * i / (n - 1))) for i in range(n)]


def _item_source_points(item, smart_group: bool, per_item_limit: int = 8):
    try:
        if smart_group:
            pts = [tuple(map(float, p[:2])) for p in item]
            if not pts:
                return []
            if len(pts) == 1:
                return [(round(pts[0][0]), round(pts[0][1]))]
            out = []
            for a, b in zip(pts, pts[1:]):
                if a == b:
                    continue
                out.extend(_line_points(a, b, max(2, min(per_item_limit, 1 + round(hypot(b[0]-a[0], b[1]-a[1]))))))
            return out or [(round(pts[0][0]), round(pts[0][1]))]
        x0, y0, x1, y1 = map(float, item[:4])
        return _line_points((x0, y0), (x1, y1), max(2, min(per_item_limit, 1 + round(hypot(x1-x0, y1-y0)))))
    except Exception:
        return []


def planned_batch_points(items, *, smart_group: bool, transform, sample_limit: int = 130):
    """Return deterministic screen-space sample points for one planned batch."""
    raw = []
    for item in items or ():
        raw.extend(_item_source_points(item, smart_group, 9))
    if not raw:
        return []
    if len(raw) > sample_limit:
        step = max(1, len(raw) // sample_limit)
        raw = raw[::step][:sample_limit]
    result = []
    seen = set()
    for x, y in raw:
        px, py = transform(int(x), int(y))
        point = (int(round(px)), int(round(py)))
        if point not in seen:
            result.append(point); seen.add(point)
    return result


def planned_batch_boxes(items, *, smart_group: bool, transform, brush_px: int = 1, pad_extra: int = 8):
    """Return padded screen-space bounding boxes for expected changed regions."""
    boxes = []
    pad = max(4, int(round(max(1, int(brush_px)) / 2)) + int(pad_extra))
    for item in items or ():
        points = _item_source_points(item, smart_group, 16)
        if not points:
            continue
        screen = [transform(int(x), int(y)) for x, y in points]
        xs = [int(round(p[0])) for p in screen]; ys = [int(round(p[1])) for p in screen]
        boxes.append((min(xs)-pad, min(ys)-pad, max(xs)+pad, max(ys)+pad))
    return merge_boxes(boxes)


def merge_boxes(boxes, *, max_boxes: int = 80):
    boxes = [tuple(map(int, b)) for b in boxes if b and len(b) == 4]
    if not boxes:
        return []
    merged = []
    for box in boxes:
        x0, y0, x1, y1 = box
        if x1 < x0 or y1 < y0:
            continue
        placed = False
        for i, current in enumerate(merged):
            a0, b0, a1, b1 = current
            if not (x1 < a0 or x0 > a1 or y1 < b0 or y0 > b1):
                merged[i] = (min(a0, x0), min(b0, y0), max(a1, x1), max(b1, y1))
                placed = True
                break
        if not placed:
            merged.append((x0, y0, x1, y1))
    # second pass catches boxes that became adjacent after earlier merges
    changed = True
    while changed and len(merged) > 1:
        changed = False
        out = []
        for box in merged:
            placed = False
            for i, current in enumerate(out):
                x0, y0, x1, y1 = box; a0, b0, a1, b1 = current
                if not (x1 < a0 or x0 > a1 or y1 < b0 or y0 > b1):
                    out[i] = (min(a0, x0), min(b0, y0), max(a1, x1), max(b1, y1))
                    changed = True; placed = True; break
            if not placed:
                out.append(box)
        merged = out
    if len(merged) <= max_boxes:
        return merged
    # Many tiny stroke boxes are expensive for outside-diff checks. Collapse to
    # one broad box; this is conservative and reduces false fill-leak alarms.
    xs0, ys0, xs1, ys1 = zip(*merged)
    return [(min(xs0), min(ys0), max(xs1), max(ys1))]


def _contains(point, boxes):
    x, y = point
    for x0, y0, x1, y1 in boxes:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


def _snapshot_xy(point, area):
    x, y = map(int, point); ax, ay, _w, _h = map(int, area)
    return x - ax, y - ay


def _near_colors(image, sx, sy, radius):
    w, h = image.size
    values = []
    for y in range(max(0, sy-radius), min(h, sy+radius+1)):
        for x in range(max(0, sx-radius), min(w, sx+radius+1)):
            values.append(tuple(map(int, image.getpixel((x, y))[:3])))
    return values


def compare_batch_snapshot(after, before, area, expected_rgb, planned_points, expected_boxes, *, brush_px: int = 1, mode: str = "Balanced"):
    """Compare one canvas snapshot against the expected effects of a color batch."""
    if mode == "Off":
        return {'ok': True, 'mode': 'Off', 'issues': [], 'confidence': 100.0}
    cfg = _mode_config(mode)
    after = after.convert('RGB')
    before = before.convert('RGB') if before is not None else None
    expected = tuple(map(int, expected_rgb[:3]))
    radius = max(1, min(5, int(round(max(1, int(brush_px)) / 2)) + 1))
    matched = 0; sampled = 0; best_error = 999; best_color = None
    for point in planned_points or []:
        sx, sy = _snapshot_xy(point, area)
        if not (0 <= sx < after.width and 0 <= sy < after.height):
            continue
        sampled += 1
        colors = _near_colors(after, sx, sy, radius)
        if not colors:
            continue
        err, color = min((rgb_error(c, expected), c) for c in colors)
        if err <= cfg['tolerance']:
            matched += 1
        if err < best_error:
            best_error, best_color = err, color
    match_rate = matched / sampled if sampled else 1.0

    changed_outside = 0; changed_total = 0; grid_samples = 0
    if before is not None and before.size == after.size:
        # bounded grid; this detects large fills/strokes outside the planned batch.
        target = max(1, int(cfg['max_outside_samples']) * 9)
        step = max(1, int((after.width * after.height / target) ** 0.5))
        for y in range(0, after.height, step):
            for x in range(0, after.width, step):
                grid_samples += 1
                a = tuple(map(int, after.getpixel((x, y))[:3])); b = tuple(map(int, before.getpixel((x, y))[:3]))
                if rgb_error(a, b) > 42:
                    changed_total += 1
                    screen = (int(area[0]) + x, int(area[1]) + y)
                    if not _contains(screen, expected_boxes):
                        changed_outside += 1
    outside_rate = changed_outside / grid_samples if grid_samples else 0.0
    issues = []
    if sampled >= 2 and match_rate < cfg['min_match']:
        issues.append('missed-region-or-wrong-color')
    if changed_outside > cfg['max_outside_samples'] or outside_rate > cfg['max_outside']:
        issues.append('outside-change-possible-fill-leak-or-wrong-place')
    confidence = max(0.0, min(100.0, match_rate * 100.0 - outside_rate * 240.0))
    return {
        'ok': not issues,
        'mode': mode,
        'issues': issues,
        'expected': expected,
        'sampled_points': sampled,
        'matched_points': matched,
        'match_rate': match_rate,
        'best_error': int(best_error if best_error != 999 else 0),
        'best_color': best_color or expected,
        'changed_total_samples': changed_total,
        'changed_outside_samples': changed_outside,
        'outside_change_rate': outside_rate,
        'confidence': confidence,
    }


def summarize_result(result) -> str:
    if not result or result.get('mode') == 'Off':
        return 'visual verification off'
    issues = result.get('issues') or []
    if not issues:
        return (f"visual OK · {result.get('matched_points',0)}/{result.get('sampled_points',0)} planned probes matched · "
                f"outside changes {result.get('changed_outside_samples',0)}")
    return (f"visual warning: {', '.join(issues)} · {result.get('matched_points',0)}/{result.get('sampled_points',0)} probes matched · "
            f"outside changes {result.get('changed_outside_samples',0)} · closest {result.get('best_color')}")
