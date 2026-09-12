from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected rc13 patch anchor missing in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new, count), encoding="utf-8")


CALIBRATION_HEALTH = dedent(r'''\
"""Profile-scoped calibration confidence for Image Draw Bot rc13.

Pure scoring only: this module never captures the screen or sends native input.
Safety-critical palette/layout evidence carries more weight than optional timing
learning, so a fast historical ETA can never mask stale target geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _clamp(value, low=0.0, high=1.0):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        value = 0.0
    return max(float(low), min(float(high), value))


def _state_score(item: dict[str, Any] | None, *, optional=False) -> float:
    item = dict(item or {})
    state = str(item.get("state") or "unavailable").lower()
    available = bool(item.get("available"))
    confidence = item.get("confidence")
    if confidence is not None:
        base = _clamp(confidence)
    elif state == "verified":
        base = 1.0
    elif state == "calibrated":
        base = .82
    elif state == "estimated":
        base = .55
    elif optional and not available:
        base = .78
    else:
        base = 0.0
    if state == "verified":
        base = max(base, .94)
    elif state == "calibrated":
        base = max(base, .72)
    return _clamp(base)


def _palette_score(item: dict[str, Any] | None) -> float:
    item = dict(item or {})
    verification = dict(item.get("verification") or {})
    score = _state_score(item)
    if verification:
        score = max(score, _clamp(verification.get("confidence")))
    count = max(0, int(item.get("count") or 0))
    if count <= 0:
        return 0.0
    if count < 3:
        score = min(score, .35)
    return _clamp(score)


def _timing_score(item: dict[str, Any] | None) -> float:
    item = dict(item or {})
    samples = max(0, int(item.get("samples") or 0))
    if samples <= 0:
        return .55
    depth = min(1.0, samples / 5.0)
    try:
        mape = float(item.get("mape")) if item.get("mape") is not None else .18
    except (TypeError, ValueError, OverflowError):
        mape = .18
    quality = max(.20, 1.0 - min(1.0, max(0.0, mape)))
    return _clamp(.55 + .45 * depth * quality)


def _layout_score(delta) -> float:
    if delta is None:
        return 1.0
    if not bool(getattr(delta, "changed", False)):
        return 1.0
    reasons = " ".join(getattr(delta, "reasons", ()) or ()).lower()
    if "dpi " in reasons or "client resize" in reasons:
        return .20
    canvas = max(0, int(getattr(delta, "max_canvas_shift", 0) or 0))
    palette = max(0, int(getattr(delta, "max_palette_shift", 0) or 0))
    shift = max(canvas, palette)
    if shift <= 6:
        return .76
    if shift <= 18:
        return .55
    return .28


@dataclass(frozen=True)
class CalibrationHealth:
    score: float
    level: str
    component_confidence: dict[str, float]
    recalibrate_components: tuple[str, ...]
    blocking: bool
    reason: str

    def as_dict(self):
        return {
            "score": round(float(self.score), 4),
            "level": self.level,
            "component_confidence": {k: round(float(v), 4) for k, v in self.component_confidence.items()},
            "recalibrate_components": list(self.recalibrate_components),
            "blocking": bool(self.blocking),
            "reason": self.reason,
        }


def summarize_calibration_health(summary: dict[str, Any], *, layout_delta=None) -> CalibrationHealth:
    palette = _palette_score(summary.get("palette"))
    tools = _state_score(summary.get("tools"), optional=True)
    exact = _state_score(summary.get("exact_color"), optional=True)
    timing = _timing_score(summary.get("timing"))
    layout = _layout_score(layout_delta)
    components = {
        "palette": palette,
        "tools": tools,
        "exact_color": exact,
        "timing": timing,
        "layout": layout,
    }
    weights = {"palette": .34, "tools": .16, "exact_color": .10, "timing": .08, "layout": .32}
    score = sum(components[key] * weights[key] for key in weights)
    recalibrate = []
    if palette < .70:
        recalibrate.append("palette")
    if tools < .55:
        recalibrate.append("tools")
    if exact < .50:
        recalibrate.append("exact_color")
    if layout < .70:
        recalibrate.append("layout")
    blocking = palette < .50 or layout < .40
    if blocking:
        level = "unsafe"
    elif score >= .90:
        level = "verified"
    elif score >= .76:
        level = "healthy"
    else:
        level = "degraded"
    reason = "calibration evidence is current" if not recalibrate else "refresh " + ", ".join(recalibrate)
    return CalibrationHealth(_clamp(score), level, components, tuple(recalibrate), blocking, reason)
''')
Path("CalibrationHealth.py").write_text(CALIBRATION_HEALTH, encoding="utf-8")


# Browser recalibration planner/retry helpers.
p = Path("BrowserAutoRecalibration.py")
text = p.read_text(encoding="utf-8")
if "class RecalibrationPlan:" not in text:
    text = text.rstrip() + dedent(r'''


@dataclass(frozen=True)
class RecalibrationPlan:
    action: str
    reason: str
    confidence: float
    safe_to_reuse_palette: bool
    safe_to_reuse_canvas: bool
    retry_delay_seconds: float = 0.0

    def as_dict(self):
        return {
            "action": self.action,
            "reason": self.reason,
            "confidence": round(float(self.confidence), 4),
            "safe_to_reuse_palette": bool(self.safe_to_reuse_palette),
            "safe_to_reuse_canvas": bool(self.safe_to_reuse_canvas),
            "retry_delay_seconds": round(float(self.retry_delay_seconds), 4),
        }


def adaptive_retry_delay(attempt: int, confidence: float | None = None) -> float:
    """Small bounded settle delay for a read-only re-scan; never an input delay."""
    n = max(0, int(attempt or 0))
    try:
        confidence = float(confidence) if confidence is not None else .68
    except (TypeError, ValueError, OverflowError):
        confidence = .68
    deficit = max(0.0, min(1.0, .82 - confidence))
    return round(min(.45, .09 + n * .09 + deficit * .32), 3)


def plan_recalibration(delta: BrowserLayoutDelta | None, *, palette_confidence: float = 1.0,
                       canvas_confidence: float = 1.0, attempt: int = 0) -> RecalibrationPlan:
    pc = max(0.0, min(1.0, float(palette_confidence or 0.0)))
    cc = max(0.0, min(1.0, float(canvas_confidence or 0.0)))
    reasons = tuple(getattr(delta, "reasons", ()) or ()) if delta is not None else ()
    text = " ".join(reasons).lower()
    canvas_changed = bool(getattr(delta, "max_canvas_shift", 0) > 0 or "canvas " in text)
    palette_changed = bool(getattr(delta, "max_palette_shift", 0) > 0 or "palette " in text)
    structural = "client resize" in text or "dpi " in text or "canvas detection changed" in text
    low_palette = pc < .70
    low_canvas = cc < .68
    if structural or (canvas_changed and palette_changed) or (low_palette and low_canvas):
        action = "full"
        reason = ", ".join(reasons) or "palette and canvas confidence are both low"
    elif canvas_changed or low_canvas:
        action = "canvas-only"
        reason = ", ".join(reasons) or f"canvas confidence {cc:.2f}"
    elif palette_changed or low_palette:
        action = "palette-only"
        reason = ", ".join(reasons) or f"palette confidence {pc:.2f}"
    else:
        action = "none"
        reason = "layout and calibration confidence are stable"
    confidence = max(0.0, min(1.0, .52 * pc + .48 * cc))
    delay = adaptive_retry_delay(attempt, min(pc, cc)) if action != "none" else 0.0
    return RecalibrationPlan(
        action, reason, confidence,
        safe_to_reuse_palette=(action in ("none", "canvas-only") and pc >= .70),
        safe_to_reuse_canvas=(action in ("none", "palette-only") and cc >= .68),
        retry_delay_seconds=delay,
    )


def evaluate_cached_canvas(cached_box, detected_box, canvas_confidence: float, *,
                           tolerance_px: int = 4, max_partial_shift_px: int = 28) -> RecalibrationPlan:
    """Decide whether a verified cached palette can survive a canvas-only drift."""
    try:
        old = tuple(map(int, cached_box))
        new = tuple(map(int, detected_box))
        if len(old) != 4 or len(new) != 4:
            raise ValueError
    except Exception:
        delta = BrowserLayoutDelta(True, ("canvas detection changed",), 0, 999)
        return plan_recalibration(delta, palette_confidence=1.0, canvas_confidence=canvas_confidence)
    shift = max(abs(a - b) for a, b in zip(old, new))
    conf = max(0.0, min(1.0, float(canvas_confidence or 0.0)))
    if conf < .68:
        return RecalibrationPlan(
            "full", f"canvas confidence {conf:.2f}", .5 * (1.0 + conf), True, False,
            adaptive_retry_delay(0, conf),
        )
    if shift <= max(0, int(tolerance_px)):
        return RecalibrationPlan("none", "cached canvas matches live detection", .5 * (1.0 + conf), True, True, 0.0)
    if shift <= max(int(tolerance_px) + 1, int(max_partial_shift_px)):
        delta = BrowserLayoutDelta(True, (f"canvas drift {shift}px",), 0, shift)
        return plan_recalibration(delta, palette_confidence=1.0, canvas_confidence=conf)
    return RecalibrationPlan(
        "full", f"large canvas reflow {shift}px", .5 * (1.0 + conf), True, False,
        adaptive_retry_delay(0, conf),
    )


def _confidence_from_error(error: BaseException) -> float | None:
    import re
    match = re.search(r"(\d{1,3})%", str(error or ""))
    if not match:
        return None
    return max(0.0, min(1.0, int(match.group(1)) / 100.0))


def calibrate_browser_with_retry(profile_key, target_metadata, palette_path, *, screenshot=None,
                                 recapture=None, max_attempts: int = 3, cancelled=lambda: False,
                                 sleep_fn=None):
    """Retry only transient read-only visual confidence failures.

    Geometry/DPI/safety errors are never retried here; callers must refresh target
    metadata instead. Successful calibration is still produced by the existing
    BrowserAutoCalibration implementation.
    """
    import time
    from BrowserAutoCalibration import auto_calibrate_browser
    if sleep_fn is None:
        sleep_fn = time.sleep
    attempts = max(1, min(3, int(max_attempts or 1)))
    current = screenshot
    errors = []
    delays = []
    transient = (
        "confidence is too low",
        "verified colors",
        "palette grid could not be verified",
        "show the whole palette",
    )
    for attempt in range(attempts):
        if cancelled():
            raise InterruptedError("Browser recalibration cancelled.")
        try:
            result = auto_calibrate_browser(profile_key, target_metadata, palette_path, screenshot=current)
            return result, {
                "attempts": attempt + 1,
                "retries": attempt,
                "errors": tuple(errors),
                "delays": tuple(delays),
            }
        except ValueError as error:
            message = str(error).lower()
            errors.append(str(error))
            if attempt + 1 >= attempts or not any(token in message for token in transient):
                raise
            delay = adaptive_retry_delay(attempt, _confidence_from_error(error))
            delays.append(delay)
            sleep_fn(delay)
            if cancelled():
                raise InterruptedError("Browser recalibration cancelled.")
            if recapture is not None:
                current = recapture()
    raise RuntimeError("Browser recalibration retry loop exhausted unexpectedly.")
''') + "\n"
p.write_text(text, encoding="utf-8")


# Calibration summary gains timing evidence + safety-weighted health.
replace(
    "CalibrationState.py",
    '''def profile_calibration_summary(profile_key: str, *, palette_path: Path | None = None,\n                                preset_available: bool = False, workflow: str = "",\n                                context_fingerprint: str | None = None) -> dict:\n''',
    '''def profile_calibration_summary(profile_key: str, *, palette_path: Path | None = None,\n                                preset_available: bool = False, workflow: str = "",\n                                context_fingerprint: str | None = None,\n                                timing_options: dict | None = None) -> dict:\n''',
)
replace(
    "CalibrationState.py",
    '''    palette = palette_state(key, palette_path=palette_path, preset_available=preset_available)\n    tools = tool_state(key)\n    exact = exact_color_state(key, workflow=workflow, context_fingerprint=context_fingerprint)\n    return {\n        "profile_key": key,\n        "palette": palette,\n        "tools": tools,\n        "exact_color": exact,\n        "fingerprint": str(context_fingerprint or calibration_context_fingerprint(key, workflow=workflow, palette_path=palette_path)),\n        "timing_file": str(profile_timing_file(key)),\n    }\n''',
    '''    palette = palette_state(key, palette_path=palette_path, preset_available=preset_available)\n    tools = tool_state(key)\n    exact = exact_color_state(key, workflow=workflow, context_fingerprint=context_fingerprint)\n    timing_input = dict(timing_options or {})\n    timing_input["profile_key"] = key\n    timing = timing_state(timing_input)\n    result = {\n        "profile_key": key,\n        "palette": palette,\n        "tools": tools,\n        "exact_color": exact,\n        "timing": timing,\n        "fingerprint": str(context_fingerprint or calibration_context_fingerprint(key, workflow=workflow, palette_path=palette_path)),\n        "timing_file": str(profile_timing_file(key)),\n    }\n    try:\n        from CalibrationHealth import summarize_calibration_health\n        result["health"] = summarize_calibration_health(result).as_dict()\n    except Exception as error:\n        result["health"] = {"level":"unknown","score":0.0,"blocking":False,"reason":str(error)}\n    return result\n''',
)
replace(
    "CalibrationState.py",
    '''    return {"state": "calibrated" if learned else "estimated", "available": learned,\n            "samples": int(info.get("samples") or 0), "ratio": float(info.get("ratio") or 1.0)}\n''',
    '''    return {"state": "calibrated" if learned else "estimated", "available": learned,\n            "samples": int(info.get("samples") or 0), "ratio": float(info.get("ratio") or 1.0),\n            "mape": info.get("mape"), "operation_runtime_source": info.get("operation_runtime_source", "none")}\n''',
)


# Runtime browser recalibration: independently verify live canvas on cache hit.
replace(
    "DrawBot.py",
    '''        cached=try_restore(profile_key,meta,Path(self.calibration_path),screenshot=screenshot)\n        cache_hit=bool(cached.hit)\n        if cache_hit:\n            class _CachedResult:\n                canvas_box=cached.canvas_box\n                canvas_confidence=max(.90,cached.confidence)\n                palette_count=cached.palette_count\n                confidence=cached.confidence\n                method='Layout Fingerprint v2 cache'\n            result=_CachedResult()\n        else:\n            result=auto_calibrate_browser(profile_key,meta,Path(self.calibration_path),screenshot=screenshot)\n''',
    '''        cached=try_restore(profile_key,meta,Path(self.calibration_path),screenshot=screenshot)\n        cache_hit=bool(cached.hit);cache_refresh_meta=None\n        retry_meta={'attempts':0,'retries':0,'errors':(), 'delays':()}\n        if cache_hit:\n            from BrowserAutoCalibration import detect_browser_canvas\n            from BrowserAutoRecalibration import evaluate_cached_canvas\n            live_canvas=detect_browser_canvas(profile_key,screenshot,screen_origin=(client[0],client[1]))\n            cache_refresh_meta=evaluate_cached_canvas(cached.canvas_box,live_canvas.get('canvas_box'),live_canvas.get('canvas_confidence',0.0))\n            if cache_refresh_meta.action=='full':\n                cache_hit=False\n            else:\n                refreshed_canvas=(live_canvas.get('canvas_box') if cache_refresh_meta.action=='canvas-only' else cached.canvas_box)\n                class _CachedResult:\n                    canvas_box=refreshed_canvas\n                    canvas_confidence=float(live_canvas.get('canvas_confidence') or max(.90,cached.confidence))\n                    palette_count=cached.palette_count\n                    confidence=cached.confidence\n                    method=('Layout Fingerprint v2 cache + canvas-only refresh' if cache_refresh_meta.action=='canvas-only' else 'Layout Fingerprint v2 cache')\n                result=_CachedResult()\n                if cache_refresh_meta.action=='canvas-only' and refreshed_canvas:\n                    try:record_from_calibration_file(profile_key,meta,refreshed_canvas,Path(self.calibration_path),method=result.method)\n                    except Exception as fingerprint_error:log_event(f'rc13 canvas-only fingerprint refresh skipped: {fingerprint_error!r}')\n        if not cache_hit:\n            from BrowserAutoRecalibration import calibrate_browser_with_retry\n            result,retry_meta=calibrate_browser_with_retry(\n                profile_key,meta,Path(self.calibration_path),screenshot=screenshot,\n                recapture=lambda:ImageGrab.grab(bbox=client,all_screens=True).convert('RGB'),\n                cancelled=self.stop.is_set)\n''',
)
replace(
    "DrawBot.py",
    '''        after=DrawBotApp._browser_layout_state(self,client_rect=client,dpi=meta.get('dpi'))\n        delta=compare_layout_states(before,after,tolerance_px=4)\n        self.canvas_anchor_transform_meta={\n            'method':'browser-visual-recalibration','changed':bool(delta.changed),\n            'reason':delta.reason,'max_palette_shift':int(delta.max_palette_shift),\n            'max_canvas_shift':int(delta.max_canvas_shift),\n            'confidence':float(result.confidence),\n        }\n''',
    '''        after=DrawBotApp._browser_layout_state(self,client_rect=client,dpi=meta.get('dpi'))\n        delta=compare_layout_states(before,after,tolerance_px=4)\n        from BrowserAutoRecalibration import plan_recalibration\n        recalibration_plan=plan_recalibration(delta,palette_confidence=float(result.confidence),\n                                              canvas_confidence=float(result.canvas_confidence))\n        self.canvas_anchor_transform_meta={\n            'method':'browser-visual-recalibration','changed':bool(delta.changed),\n            'reason':delta.reason,'max_palette_shift':int(delta.max_palette_shift),\n            'max_canvas_shift':int(delta.max_canvas_shift),\n            'confidence':float(result.confidence),\n            'canvas_confidence':float(result.canvas_confidence),\n            'recalibration_plan':recalibration_plan.as_dict(),\n            'cache_refresh':cache_refresh_meta.as_dict() if cache_refresh_meta is not None else None,\n            'retry_meta':dict(retry_meta),\n        }\n''',
)


# One-click full calibration uses the same bounded read-only retries.
replace(
    "BrowserOneClick.py",
    '''    result=auto_calibrate_browser(key,meta,Path(palette_path),screenshot=screenshot)\n    try:fingerprint=record_from_calibration_file(key,meta,result.canvas_box,Path(palette_path),method='Browser One-Click / '+result.method) if result.canvas_box else None\n''',
    '''    from BrowserAutoRecalibration import calibrate_browser_with_retry\n    result,retry_meta=calibrate_browser_with_retry(\n        key,meta,Path(palette_path),screenshot=screenshot,\n        recapture=lambda:ImageGrab.grab(bbox=tuple(meta['client_rect']),all_screens=True).convert('RGB'))\n    try:fingerprint=record_from_calibration_file(key,meta,result.canvas_box,Path(palette_path),method='Browser One-Click / '+result.method) if result.canvas_box else None\n''',
)
replace(
    "BrowserOneClick.py",
    '''    payload=result.as_dict();payload.update({'target_meta':meta,'profile_name':profile_name,'layout_fingerprint_meta':fingerprint,'one_click':True})\n''',
    '''    payload=result.as_dict();payload.update({'target_meta':meta,'profile_name':profile_name,'layout_fingerprint_meta':fingerprint,'one_click':True,'recalibration_retry_meta':retry_meta})\n''',
)

replace(
    "build_exe.py",
    "        '--hidden-import', 'BrowserAutoRecalibration',\n",
    "        '--hidden-import', 'BrowserAutoRecalibration',\n        '--hidden-import', 'CalibrationHealth',\n",
)


# Version and release surfaces.
replace("Version.py", "APP_VERSION = '1.0.145-rc12'", "APP_VERSION = '1.0.145-rc13'")
replace("installer/ImageDrawBot.iss", '#define MyAppVersion "1.0.145-rc12"', '#define MyAppVersion "1.0.145-rc13"')
for test in Path(".").glob("test_*.py"):
    raw = test.read_text(encoding="utf-8")
    if "1.0.145-rc12" in raw:
        test.write_text(raw.replace("1.0.145-rc12", "1.0.145-rc13"), encoding="utf-8")
for name in (
    "README.md", "docs/wiki/Installation.md", "docs/README.md", "README-INDEX.md",
    "docs/wiki/Home.md", "docs/wiki/Updates.md",
):
    p = Path(name)
    if p.exists():
        p.write_text(p.read_text(encoding="utf-8").replace("1.0.145-rc12", "1.0.145-rc13"), encoding="utf-8")

notes = '''# Image Draw Bot v1.0.145-rc13 — Calibration & Recovery

- Add a profile-scoped Calibration Health score with separate palette, tool, exact-color, timing and layout confidence.
- Re-verify the live browser canvas even when Layout Fingerprint v2 already verified the cached palette.
- Perform canvas-only recalibration for small safe canvas drift while retaining the independently verified palette.
- Escalate DPI changes, large reflow and low canvas confidence to full read-only browser recalibration.
- Add bounded adaptive retries for transient visual palette-confidence failures; geometry/safety failures are never retried blindly.
- Export recalibration action, cache-refresh decision and retry telemetry into runtime calibration metadata.
'''
Path("RELEASE-NOTES-v1.0.145-rc13.md").write_text(notes, encoding="utf-8")
history = '''# Image Draw Bot v1.0.145-rc13 — Calibration & Recovery

- Calibration state now exposes component confidence and an overall safety-weighted health score.
- Cached browser palettes can survive a small canvas-only drift, avoiding unnecessary full palette recalibration.
- Large layout/DPI changes still force full recalibration before mouse input.
- Transient read-only calibration failures receive bounded adaptive retries.

'''
for name in ("VERSION-HISTORY.md", "docs/VERSION-HISTORY.md"):
    p = Path(name)
    p.write_text(history + p.read_text(encoding="utf-8"), encoding="utf-8")


TEST = dedent(r'''\
import unittest
from pathlib import Path
from unittest.mock import patch

from BrowserAutoRecalibration import (
    BrowserLayoutDelta, calibrate_browser_with_retry, evaluate_cached_canvas, plan_recalibration,
)
from CalibrationHealth import summarize_calibration_health
from Version import APP_VERSION


class Rc13CalibrationRecoveryTests(unittest.TestCase):
    def test_small_canvas_drift_is_partial(self):
        plan = evaluate_cached_canvas((100,100,900,600), (106,103,906,603), .91)
        self.assertEqual(plan.action, 'canvas-only')
        self.assertTrue(plan.safe_to_reuse_palette)
        self.assertFalse(plan.safe_to_reuse_canvas)

    def test_large_canvas_drift_requires_full(self):
        plan = evaluate_cached_canvas((100,100,900,600), (150,100,950,600), .95)
        self.assertEqual(plan.action, 'full')

    def test_dpi_or_resize_requires_full(self):
        delta = BrowserLayoutDelta(True, ('DPI 96→120','client resize 1000×700→1200×840'), 0, 0)
        plan = plan_recalibration(delta, palette_confidence=.98, canvas_confidence=.98)
        self.assertEqual(plan.action, 'full')

    def test_retry_is_bounded_and_adaptive(self):
        class Result: pass
        calls=[]; sleeps=[]
        def fake(*args, **kwargs):
            calls.append(1)
            if len(calls)==1:
                raise ValueError('Palette confidence is too low (61%). Manual fallback is safer for this layout.')
            return Result()
        with patch('BrowserAutoCalibration.auto_calibrate_browser', side_effect=fake):
            result,meta=calibrate_browser_with_retry(
                'gartic-phone', {'client_rect':(0,0,100,100)}, Path('x'),
                screenshot=object(), recapture=lambda:object(), sleep_fn=sleeps.append)
        self.assertIsInstance(result, Result)
        self.assertEqual(meta['attempts'], 2)
        self.assertEqual(len(sleeps), 1)
        self.assertGreater(sleeps[0], 0)
        self.assertLessEqual(sleeps[0], .45)

    def test_non_transient_geometry_error_is_not_retried(self):
        calls=[]
        def fake(*args, **kwargs):
            calls.append(1)
            raise ValueError('Target screenshot size changed during calibration. Keep the browser window still.')
        with patch('BrowserAutoCalibration.auto_calibrate_browser', side_effect=fake):
            with self.assertRaises(ValueError):
                calibrate_browser_with_retry('gartic-phone', {}, Path('x'), screenshot=object(), sleep_fn=lambda _s:None)
        self.assertEqual(len(calls), 1)

    def test_health_weights_layout_and_palette_as_safety_evidence(self):
        summary={
            'palette':{'state':'verified','available':True,'count':48,'verification':{'confidence':.96}},
            'tools':{'state':'calibrated','available':True,'confidence':.85},
            'exact_color':{'state':'unavailable','available':False},
            'timing':{'state':'calibrated','available':True,'samples':5,'mape':.08},
        }
        good=summarize_calibration_health(summary)
        self.assertIn(good.level, ('healthy','verified'))
        self.assertFalse(good.blocking)
        bad=summarize_calibration_health(summary, layout_delta=BrowserLayoutDelta(True, ('DPI 96→144',), 0, 0))
        self.assertLess(bad.score, good.score)
        self.assertIn('layout', bad.recalibrate_components)

    def test_runtime_source_contains_partial_refresh_and_retry(self):
        src=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn('evaluate_cached_canvas', src)
        self.assertIn('calibrate_browser_with_retry', src)
        self.assertIn("'recalibration_plan':recalibration_plan.as_dict()", src)

    def test_version(self):
        self.assertEqual(APP_VERSION, '1.0.145-rc13')


if __name__ == '__main__':
    unittest.main()
''')
Path("test_rc13_calibration_recovery.py").write_text(TEST, encoding="utf-8")
