from pathlib import Path


def replace(path, old, new, count=1):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"rc5 anchor missing in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new, count), encoding="utf-8")


p = Path("RegionFillEngine.py")
text = p.read_text(encoding="utf-8")
text = text.replace("from math import ceil\n", "from math import ceil, hypot\n", 1)
anchor = "\ndef _risk(region: dict[str, Any], *, aggressiveness: str, quality: str, brush_px: int) -> tuple[float, float, str]:\n"
if anchor not in text:
    raise SystemExit("rc5 risk anchor missing")
helpers = '''

def _span_contains(region: dict[str, Any], x: int, y: int) -> bool:
    """True only when a source pixel is part of the connected fill component."""
    x = int(x); y = int(y)
    for raw in region.get("row_spans") or ():
        try:
            sy, left, right = map(int, raw)
        except Exception:
            continue
        if sy == y and left <= x <= right:
            return True
    return False


def _diagonal_seal_paths(region: dict[str, Any], *, max_paths: int = 96) -> tuple[list[tuple[tuple[int, int], tuple[int, int]]], int, int]:
    """Return inside-only bridges for one-pixel diagonal contour corners."""
    raw_points = region.get("contour") or ()
    points = []
    for raw in raw_points:
        try:
            points.append((int(raw[0]), int(raw[1])))
        except Exception:
            continue
    if len(points) < 2:
        return [], 0, 0
    pairs = list(zip(points, points[1:]))
    if points[-1] != points[0]:
        pairs.append((points[-1], points[0]))
    paths = []
    seen = set()
    total = 0
    unresolved = 0
    for a, b in pairs:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        if abs(dx) != 1 or abs(dy) != 1:
            continue
        total += 1
        candidates = ((b[0], a[1]), (a[0], b[1]))
        bridge = next((c for c in candidates if _span_contains(region, c[0], c[1])), None)
        start = a if _span_contains(region, a[0], a[1]) else (b if _span_contains(region, b[0], b[1]) else None)
        if bridge is None or start is None or len(paths) >= max(1, int(max_paths)):
            unresolved += 1
            continue
        key = (start, bridge)
        if key in seen or start == bridge:
            continue
        seen.add(key)
        paths.append(key)
    return paths, total, unresolved


def _fill_escape_prediction(region: dict[str, Any], *, brush_px: int, aggressiveness: str, quality: str) -> tuple[float, list, str]:
    """Predict contour leakage without weakening existing hard safety gates."""
    safety = max(0.0, min(1.0, float(region.get("safety_score", 0.0) or 0.0)))
    density = max(0.0, min(1.0, float(region.get("bbox_density", 0.0) or 0.0)))
    thin = _thin_neck_score(region, brush_px)
    seals, total_diag, unresolved = _diagonal_seal_paths(region)
    unresolved_ratio = (unresolved / max(1, total_diag)) if total_diag else 0.0
    diagonal_pressure = min(1.0, total_diag / max(8.0, float(len(region.get("contour") or ())) * .35)) if total_diag else 0.0
    risk = (1.0 - safety) * .46 + thin * .26 + (1.0 - density) * .08 + diagonal_pressure * .08 + unresolved_ratio * .32
    risk = max(0.0, min(1.0, risk))
    limit = {"Safe": .20, "Balanced": .32, "Aggressive": .42}.get(aggressiveness, .32)
    if quality == "High Quality":
        limit = min(limit, .26)
    elif quality == "Pixel Accurate":
        limit = min(limit, .12)
    if unresolved:
        return risk, [], f"unsealed diagonal contour corner ({unresolved})"
    if risk > limit:
        return risk, [], f"fill escape risk {risk:.2f} > {limit:.2f}"
    if seals:
        return risk, seals, "sealed"
    return risk, [], "safe"


def _seal_cost_seconds(paths, options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> float:
    if not paths:
        return 0.0
    delivery = resolve_stroke_delivery(options, dry_run=False)
    speed_name = normalize_speed(options.get("speed", "Balanced"))
    delay = float(options.get("delay", 0.0) or 0.0)
    path_delay = max(float(delivery.min_path_delay), float(phase_delay(delay, speed_name, "path")))
    travel_delay = max(.002, float(phase_delay(delay, speed_name, "travel")))
    boundary_delay = max(.004, float(phase_delay(delay, speed_name, "boundary")))
    step = max(1.0, float(delivery.step_px))
    iw, ih = max(1, int(image_size[0])), max(1, int(image_size[1]))
    fw, fh = max(1, int(fitted[0])), max(1, int(fitted[1]))
    sx, sy = fw / iw, fh / ih
    total = 0.0
    for raw_path in paths:
        pts = []
        for raw in raw_path or ():
            try:
                pts.append((int(raw[0]), int(raw[1])))
            except Exception:
                continue
        if len(pts) < 2:
            continue
        length = sum(hypot((b[0] - a[0]) * sx, (b[1] - a[1]) * sy) for a, b in zip(pts, pts[1:]))
        moves = max(1, int(ceil(length / step)))
        total += travel_delay + moves * path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
    return max(0.0, total)
'''
text = text.replace(anchor, helpers + anchor, 1)

old = '''    stroke_cost, fill_cost = _region_cost(region, options, image_size, fitted)\n    batchable = max(0.0, min(_batchable_tool_cost(options), fill_cost * .50))\n    fill_core = max(.001, fill_cost - batchable)\n    return stroke_cost, fill_cost, fill_core, batchable\n'''
new = '''    stroke_cost, fill_cost = _region_cost(region, options, image_size, fitted)\n    seal_cost = _seal_cost_seconds(region.get("fill_seal_paths") or (), options, image_size, fitted)\n    fill_cost += seal_cost\n    batchable = max(0.0, min(_batchable_tool_cost(options), fill_cost * .50))\n    fill_core = max(.001, fill_cost - batchable)\n    return stroke_cost, fill_cost, fill_core, batchable\n'''
if old not in text:
    raise SystemExit("rc5 cost anchor missing")
text = text.replace(old, new, 1)

old = '''        risk, confidence, safety_reason = _risk(\n            region, aggressiveness=aggressiveness, quality=quality, brush_px=brush_px\n        )\n        stroke_cost, fill_cost, fill_core, batchable = _region_cost_components(region, options, image.size, fitted)\n'''
new = '''        risk, confidence, safety_reason = _risk(\n            region, aggressiveness=aggressiveness, quality=quality, brush_px=brush_px\n        )\n        escape_risk, seal_paths, escape_reason = _fill_escape_prediction(\n            region, brush_px=brush_px, aggressiveness=aggressiveness, quality=quality)\n        if seal_paths:\n            region["fill_seal_paths"] = [tuple(path) for path in seal_paths]\n        stroke_cost, fill_cost, fill_core, batchable = _region_cost_components(region, options, image.size, fitted)\n        seal_cost = _seal_cost_seconds(seal_paths, options, image.size, fitted)\n'''
if old not in text:
    raise SystemExit("rc5 build loop anchor missing")
text = text.replace(old, new, 1)
text = text.replace('''        safety_ok = safety_reason == "safe"\n        accepted_here = bool(safety_ok and cost_ok and value_ok)\n''', '''        safety_ok = safety_reason == "safe" and escape_reason in ("safe", "sealed")\n        accepted_here = bool(safety_ok and cost_ok and value_ok)\n''', 1)
text = text.replace('''        if not safety_ok:\n            rejected_safety += 1\n            reason = safety_reason\n''', '''        if not safety_ok:\n            rejected_safety += 1\n            reason = safety_reason if safety_reason != "safe" else escape_reason\n''', 1)
old = '''                "seconds_saved_per_visual_error": round(seconds_per_error, 4),\n                "outline_simplification": "exact-collinear",\n'''
new = '''                "seconds_saved_per_visual_error": round(seconds_per_error, 4),\n                "fill_escape_risk": round(escape_risk, 5),\n                "fill_seal_count": len(seal_paths),\n                "fill_seal_cost_seconds": round(seal_cost, 5),\n                "fill_strategy": "OUTLINE_SEAL_FILL" if seal_paths else "OUTLINE_FILL",\n                "outline_simplification": "exact-collinear",\n'''
if old not in text:
    raise SystemExit("rc5 accepted metadata anchor missing")
text = text.replace(old, new, 1)
old = '''        "fill_color_batches": fill_colors,\n        "outline_simplification": "exact-collinear only",\n'''
new = '''        "fill_color_batches": fill_colors,\n        "fill_sealed_regions": sum(1 for r in accepted if r.get("fill_seal_count")),\n        "fill_seal_paths": sum(int(r.get("fill_seal_count", 0) or 0) for r in accepted),\n        "fill_escape_prediction": "diagonal-corner preseal v1",\n        "outline_simplification": "exact-collinear only",\n'''
if old not in text:
    raise SystemExit("rc5 meta anchor missing")
text = text.replace(old, new, 1)

old = """        risk,confidence,safety_reason=_risk(region,aggressiveness=aggressiveness,quality=quality,brush_px=brush_px)\n        stroke_cost,fill_cost,fill_core,batchable=_region_cost_components(region,options,image_size,fitted)\n"""
new = """        risk,confidence,safety_reason=_risk(region,aggressiveness=aggressiveness,quality=quality,brush_px=brush_px)\n        escape_risk,seal_paths,escape_reason=_fill_escape_prediction(region,brush_px=brush_px,aggressiveness=aggressiveness,quality=quality)\n        if seal_paths:region['fill_seal_paths']=[tuple(path) for path in seal_paths]\n        stroke_cost,fill_cost,fill_core,batchable=_region_cost_components(region,options,image_size,fitted)\n        seal_cost=_seal_cost_seconds(seal_paths,options,image_size,fitted)\n"""
if old not in text:
    raise SystemExit("rc5 evaluate loop anchor missing")
text = text.replace(old, new, 1)
text = text.replace("safety_ok=safety_reason=='safe';accepted_here=bool(safety_ok and cost_ok and value_ok)", "safety_ok=safety_reason=='safe' and escape_reason in ('safe','sealed');accepted_here=bool(safety_ok and cost_ok and value_ok)", 1)
text = text.replace("if not safety_ok:rejected_safety+=1;reason=safety_reason", "if not safety_ok:rejected_safety+=1;reason=safety_reason if safety_reason!='safe' else escape_reason", 1)
old = """                           'estimated_time_saved_seconds':round(saving,5),'visual_error_cost':round(visual_error,6),\n                           'seconds_saved_per_visual_error':round(seconds_per_error,4),'outline_simplification':'exact-collinear'})\n"""
new = """                           'estimated_time_saved_seconds':round(saving,5),'visual_error_cost':round(visual_error,6),\n                           'seconds_saved_per_visual_error':round(seconds_per_error,4),'fill_escape_risk':round(escape_risk,5),\n                           'fill_seal_count':len(seal_paths),'fill_seal_cost_seconds':round(seal_cost,5),\n                           'fill_strategy':'OUTLINE_SEAL_FILL' if seal_paths else 'OUTLINE_FILL','outline_simplification':'exact-collinear'})\n"""
if old not in text:
    raise SystemExit("rc5 evaluate metadata anchor missing")
text = text.replace(old, new, 1)
old = """        'fill_color_batches':len({int(r.get('color_index',-1)) for r in accepted if int(r.get('color_index',-1))>=0}),\n        'outline_simplification':'exact-collinear only','pixel_accurate_protected':False,\n"""
new = """        'fill_color_batches':len({int(r.get('color_index',-1)) for r in accepted if int(r.get('color_index',-1))>=0}),\n        'fill_sealed_regions':sum(1 for r in accepted if r.get('fill_seal_count')),\n        'fill_seal_paths':sum(int(r.get('fill_seal_count',0) or 0) for r in accepted),'fill_escape_prediction':'diagonal-corner preseal v1',\n        'outline_simplification':'exact-collinear only','pixel_accurate_protected':False,\n"""
if old not in text:
    raise SystemExit("rc5 evaluate meta anchor missing")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

p = Path("DrawBot.py")
text = p.read_text(encoding="utf-8")
old = '''                    before=mouse.snapshot_colors(probes) if probes and hasattr(mouse,'snapshot_colors') else None\n                    contour=region.get('contour') or ()\n'''
new = '''                    before=mouse.snapshot_colors(probes) if probes and hasattr(mouse,'snapshot_colors') else None\n                    for _seal_path in region.get('fill_seal_paths',()) or ():\n                        try:_seal_points=[point(int(raw[0]),int(raw[1])) for raw in _seal_path]\n                        except (TypeError,ValueError,IndexError):continue\n                        for _seal_a,_seal_b in zip(_seal_points,_seal_points[1:]):\n                            draw_segment(_seal_a,_seal_b)\n                    contour=region.get('contour') or ()\n'''
if old not in text:
    raise SystemExit("rc5 DrawBot fill anchor missing")
p.write_text(text.replace(old, new, 1), encoding="utf-8")

p = Path("Version.py")
p.write_text(p.read_text(encoding="utf-8").replace("APP_VERSION = '1.0.145-rc4'", "APP_VERSION = '1.0.145-rc5'"), encoding="utf-8")
for test in Path(".").glob("test_*.py"):
    lines = []
    for line in test.read_text(encoding="utf-8").splitlines(True):
        if "APP_VERSION" in line and "1.0.145-rc4" in line:
            line = line.replace("1.0.145-rc4", "1.0.145-rc5")
        lines.append(line)
    test.write_text("".join(lines), encoding="utf-8")
installer = Path("installer/ImageDrawBot.iss")
installer.write_text(installer.read_text(encoding="utf-8").replace('#define MyAppVersion "1.0.145-rc4"', '#define MyAppVersion "1.0.145-rc5"'), encoding="utf-8")
for name in ("README.md", "docs/wiki/Installation.md", "docs/README.md", "README-INDEX.md", "docs/wiki/Home.md", "docs/wiki/Updates.md"):
    q = Path(name)
    q.write_text(q.read_text(encoding="utf-8").replace("1.0.145-rc4", "1.0.145-rc5"), encoding="utf-8")

notes = '''# Image Draw Bot v1.0.145-rc5 — Smart Fill Engine

- Predict diagonal contour escape risk before choosing bucket Fill.
- Add conservative contour-seal strokes only when every added pixel is proven inside the connected source region.
- Keep all existing hard Fill safety blockers authoritative; seal logic never overrides a hard rejection.
- Charge seal strokes in Fill economics so Fill is selected only when it remains faster than connected runs/strokes.
- Execute seal strokes before the contour and runtime-verified Fill operation.
- Report sealed regions, seal-path count, escape risk and seal execution cost in planner metadata.
'''
Path("RELEASE-NOTES-v1.0.145-rc5.md").write_text(notes, encoding="utf-8")
history = '''# Image Draw Bot v1.0.145-rc5 — Smart Fill Engine

- Added conservative Fill escape prediction and planner-proven contour sealing.
- Seal strokes are restricted to pixels inside the connected region and are included in real execution cost.
- Existing Fill hard blockers and runtime guard verification remain authoritative.

'''
for name in ("VERSION-HISTORY.md", "docs/VERSION-HISTORY.md"):
    q = Path(name)
    q.write_text(history + q.read_text(encoding="utf-8"), encoding="utf-8")

test_text = '''import unittest
from pathlib import Path
from RegionFillEngine import _diagonal_seal_paths, _span_contains, _region_cost_components, evaluate_region_candidates


class Rc5SmartFillTests(unittest.TestCase):
    def region(self):
        return {
            "color_index": 1,
            "row_spans": [(0, 1, 3), (1, 1, 4), (2, 1, 4), (3, 1, 4)],
            "contour": [(1, 0), (3, 0), (4, 1), (4, 3), (1, 3), (1, 0)],
            "seed_pixel": (2, 2),
            "guard_pixels": [(0, 2), (5, 2)],
            "area_pixels": 15,
            "safety_score": .99,
            "bbox_density": .94,
            "perimeter_pixels": 14,
        }

    def test_diagonal_seals_never_leave_component(self):
        r = self.region()
        paths, total, unresolved = _diagonal_seal_paths(r)
        self.assertGreaterEqual(total, 1)
        self.assertEqual(unresolved, 0)
        self.assertTrue(paths)
        for path in paths:
            for x, y in path:
                self.assertTrue(_span_contains(r, x, y), (x, y))

    def test_seal_cost_is_charged(self):
        r = self.region()
        base = dict(r)
        sealed = dict(r, fill_seal_paths=[((3, 0), (3, 1))])
        opts = {"speed": "Balanced", "delay": .003, "brush_px": 2}
        a = _region_cost_components(base, opts, (20, 20), (200, 200))
        b = _region_cost_components(sealed, opts, (20, 20), (200, 200))
        self.assertGreater(b[1], a[1])
        self.assertGreater(b[2], a[2])

    def test_hard_thin_neck_is_not_overridden(self):
        r = {
            "color_index": 1,
            "row_spans": [(y, 5, 5) for y in range(8)],
            "contour": [(5, 0), (5, 1), (5, 7), (5, 6), (5, 0)],
            "seed_pixel": (5, 3),
            "guard_pixels": [(3, 3), (7, 3)],
            "area_pixels": 8,
            "safety_score": .99,
            "bbox_density": 1.0,
            "perimeter_pixels": 16,
        }
        accepted, meta = evaluate_region_candidates(
            [r], (20, 20), (200, 200),
            {"speed": "Fast", "brush_px": 4, "fill_aggressiveness": "Aggressive", "fill_tool_available": True},
        )
        self.assertEqual(accepted, [])
        self.assertGreaterEqual(meta["rejected_by_safety"], 1)

    def test_runtime_executes_seals_before_contour(self):
        src = Path("DrawBot.py").read_text(encoding="utf-8")
        seal = src.index("for _seal_path in region.get('fill_seal_paths'")
        contour = src.index("contour=region.get('contour')", seal)
        self.assertLess(seal, contour)


if __name__ == "__main__":
    unittest.main()
'''
Path("test_rc5_smart_fill.py").write_text(test_text, encoding="utf-8")
