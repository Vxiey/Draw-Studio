"""Picture-driven custom RGB palette preparation for Microsoft Paint.

This module is intentionally separate from the drawing engine.  It analyses the
currently loaded source image with Draw Studio's existing DynamicColors planner,
keeps only custom RGB values that materially improve over the calibrated Paint
palette, enters those RGB values through the already calibrated Edit colors
controls, and persists the resulting picture palette for reuse.

The feature never paints on the canvas.  It is an explicit user action and raw
mouse input is armed only for the short UI-control sequence, then always disarmed.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from RuntimePaths import atomic_write_text, data_dir

SCHEMA = 1
PROFILE_KEY = "microsoft-paint"
DEFAULT_MAX_COLORS = 16
MAX_ANALYSIS_DIMENSION = 640
MAX_EDGE_SAMPLES = 24000


@dataclass(frozen=True)
class PicturePalette:
    image_fingerprint: str
    calibration_fingerprint: str
    source_size: tuple[int, int]
    max_colors: int
    fidelity: str
    colors: tuple[tuple[int, int, int], ...]
    custom_colors: tuple[tuple[int, int, int], ...]
    palette_colors: tuple[tuple[int, int, int], ...]
    custom_coverages: tuple[float, ...]
    cache_hit: bool = False

    def as_dict(self) -> dict:
        return {
            "version": SCHEMA,
            "profile_key": PROFILE_KEY,
            "image_fingerprint": self.image_fingerprint,
            "calibration_fingerprint": self.calibration_fingerprint,
            "source_size": list(self.source_size),
            "max_colors": int(self.max_colors),
            "fidelity": self.fidelity,
            "colors": [list(c) for c in self.colors],
            "custom_colors": [list(c) for c in self.custom_colors],
            "palette_colors": [list(c) for c in self.palette_colors],
            "custom_coverages": [float(v) for v in self.custom_coverages],
            "cache_hit": bool(self.cache_hit),
        }


def _rgb(value: Sequence[int]) -> tuple[int, int, int]:
    if not isinstance(value, (tuple, list)) or len(value) < 3:
        raise ValueError("Invalid RGB value in picture palette.")
    out = tuple(max(0, min(255, int(value[i]))) for i in range(3))
    return out


def _visible_rgb(image):
    from ColorMatchingEngine import visible_rgb_image
    return visible_rgb_image(image).convert("RGB")


def _analysis_image(image):
    from PIL import Image
    source = _visible_rgb(image)
    if max(source.size) <= MAX_ANALYSIS_DIMENSION:
        return source
    out = source.copy()
    out.thumbnail((MAX_ANALYSIS_DIMENSION, MAX_ANALYSIS_DIMENSION), Image.Resampling.LANCZOS)
    return out


def image_fingerprint(image) -> str:
    """Stable bounded fingerprint of visible source pixels plus original size."""
    from PIL import Image
    source = _visible_rgb(image)
    thumb = source.copy()
    thumb.thumbnail((512, 512), Image.Resampling.LANCZOS)
    digest = hashlib.sha256()
    digest.update(f"{source.width}x{source.height}|RGB|".encode("ascii"))
    digest.update(thumb.tobytes())
    return digest.hexdigest()


def _cache_root() -> Path:
    root = data_dir() / "picture-palettes"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cache_path(image_fp: str, calibration_fp: str = "") -> Path:
    image_key = "".join(c for c in str(image_fp).lower() if c in "0123456789abcdef")[:24]
    calibration_key = hashlib.sha256(str(calibration_fp or "none").encode("utf-8")).hexdigest()[:12]
    if len(image_key) < 12:
        raise ValueError("Invalid picture palette image fingerprint.")
    return _cache_root() / f"{PROFILE_KEY}-{image_key}-{calibration_key}.json"


def _validate_payload(payload: dict, *, image_fp: str | None = None,
                      calibration_fp: str | None = None) -> dict:
    if not isinstance(payload, dict) or int(payload.get("version", 0)) != SCHEMA:
        raise ValueError("Invalid picture custom palette cache.")
    if payload.get("profile_key") != PROFILE_KEY:
        raise ValueError("Picture custom palette belongs to another profile.")
    if image_fp is not None and payload.get("image_fingerprint") != image_fp:
        raise ValueError("Picture custom palette belongs to another image.")
    if calibration_fp is not None and payload.get("calibration_fingerprint", "") != calibration_fp:
        raise ValueError("Picture custom palette was built for another Paint calibration.")
    size = payload.get("source_size")
    if not isinstance(size, (list, tuple)) or len(size) != 2 or any(int(v) <= 0 for v in size):
        raise ValueError("Invalid picture palette source size.")
    for name in ("colors", "custom_colors", "palette_colors"):
        values = payload.get(name, [])
        if not isinstance(values, list):
            raise ValueError(f"Invalid {name} in picture palette.")
        payload[name] = [list(_rgb(v)) for v in values]
    coverages = payload.get("custom_coverages", [])
    if not isinstance(coverages, list):
        raise ValueError("Invalid picture palette coverage data.")
    payload["custom_coverages"] = [max(0.0, min(1.0, float(v))) for v in coverages]
    payload["max_colors"] = max(1, min(32, int(payload.get("max_colors", DEFAULT_MAX_COLORS))))
    payload["fidelity"] = str(payload.get("fidelity") or "Faithful")
    return payload


def load_cached_palette(image_fp: str, calibration_fp: str, *, max_colors: int,
                        fidelity: str) -> PicturePalette | None:
    path = cache_path(image_fp, calibration_fp)
    try:
        payload = _validate_payload(json.loads(path.read_text(encoding="utf-8")),
                                    image_fp=image_fp, calibration_fp=calibration_fp)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    if int(payload["max_colors"]) != int(max_colors) or payload["fidelity"] != str(fidelity):
        return None
    return PicturePalette(
        image_fp, calibration_fp, tuple(map(int, payload["source_size"])), int(payload["max_colors"]),
        str(payload["fidelity"]), tuple(_rgb(v) for v in payload["colors"]),
        tuple(_rgb(v) for v in payload["custom_colors"]), tuple(_rgb(v) for v in payload["palette_colors"]),
        tuple(float(v) for v in payload.get("custom_coverages", [])), True,
    )


def save_palette(palette: PicturePalette) -> Path:
    payload = palette.as_dict()
    payload["cache_hit"] = False
    payload["saved_at_utc"] = datetime.now(timezone.utc).isoformat()
    path = cache_path(palette.image_fingerprint, palette.calibration_fingerprint)
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def _distance2(a: Sequence[int], b: Sequence[int]) -> int:
    return sum((int(a[i]) - int(b[i])) ** 2 for i in range(3))


def _dedupe(colors: Iterable[Sequence[int]], *, threshold: int = 7) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    limit2 = int(threshold) ** 2 * 3
    for value in colors:
        rgb = _rgb(value)
        if any(_distance2(rgb, old) <= limit2 for old in out):
            continue
        out.append(rgb)
    return out


def _edge_detail_colors(image, count: int, *, cancelled=lambda: False) -> list[tuple[int, int, int]]:
    """Return a few colors sampled specifically from high-edge pixels.

    This does not replace the normal DynamicColors ranking.  It only gives tiny
    high-contrast details a chance to enter the prepared palette when coverage
    alone would put them below large flat regions.
    """
    if count <= 0 or cancelled():
        return []
    from PIL import Image, ImageFilter
    source = _analysis_image(image)
    gray = source.convert("L")
    edge = gray.filter(ImageFilter.FIND_EDGES)
    pixels = list(source.getdata())
    weights = list(edge.getdata())
    candidates = [rgb for rgb, strength in zip(pixels, weights) if int(strength) >= 52]
    if not candidates:
        return []
    step = max(1, math.ceil(len(candidates) / MAX_EDGE_SAMPLES))
    candidates = candidates[::step][:MAX_EDGE_SAMPLES]
    if cancelled():
        return []
    sample = Image.new("RGB", (max(1, len(candidates)), 1))
    sample.putdata(candidates)
    q = sample.quantize(colors=max(1, min(int(count), 16)), method=Image.Quantize.MEDIANCUT,
                        dither=Image.Dither.NONE)
    pal = q.getpalette() or []
    ranked = sorted((q.getcolors() or []), reverse=True)
    result = []
    for _n, index in ranked:
        base = int(index) * 3
        if base + 2 < len(pal):
            result.append((int(pal[base]), int(pal[base + 1]), int(pal[base + 2])))
    return _dedupe(result)


def build_picture_palette(image, palette_rgb: Iterable[Sequence[int]], *, max_colors: int = DEFAULT_MAX_COLORS,
                          fidelity: str = "Faithful", calibration_fingerprint: str = "",
                          cancelled=lambda: False) -> PicturePalette:
    """Build a bounded picture-specific palette using the production color planner."""
    from ColorFidelity import delta_e2000
    from DynamicColors import build_dynamic_color_strokes

    max_colors = max(1, min(32, int(max_colors)))
    fidelity = str(fidelity or "Faithful")
    image_fp = image_fingerprint(image)
    cached = load_cached_palette(image_fp, calibration_fingerprint, max_colors=max_colors, fidelity=fidelity)
    if cached is not None:
        return cached
    if cancelled():
        raise InterruptedError("Picture custom palette cancelled.")

    analysis = _analysis_image(image)
    fallback = tuple(_rgb(c) for c in palette_rgb)
    if not fallback:
        raise ValueError("No Paint palette colors are available. Read/calibrate the Paint palette first.")
    groups, planned, selectors, meta = build_dynamic_color_strokes(
        analysis, fallback, max_colors=max_colors, skip_white=False, lines=True,
        exact_available=True, color_fidelity=fidelity, profile_name="Microsoft Paint",
        cancelled=cancelled,
    )
    if groups is None:
        raise InterruptedError("Picture custom palette cancelled.")
    planned = tuple(_rgb(c) for c in (planned or ()))
    selectors = tuple(selectors or ())
    coverages = tuple((meta or {}).get("coverage_priority") or ())

    custom: list[tuple[int, int, int]] = []
    custom_cov: list[float] = []
    palette_colors: list[tuple[int, int, int]] = []
    for index, selector in enumerate(selectors):
        if cancelled():
            raise InterruptedError("Picture custom palette cancelled.")
        if index >= len(groups) or not groups[index]:
            continue
        coverage = float(coverages[index]) if index < len(coverages) else 0.0
        if selector.get("kind") == "custom":
            rgb = _rgb(selector.get("rgb", planned[index] if index < len(planned) else (0, 0, 0)))
            if rgb not in custom:
                custom.append(rgb); custom_cov.append(coverage)
        else:
            rgb = _rgb(planned[index] if index < len(planned) else selector.get("rgb", (0, 0, 0)))
            if rgb not in palette_colors:
                palette_colors.append(rgb)

    # Reserve up to a quarter of the custom budget for high-edge colors that are
    # materially different from the normal Paint palette.  This protects eyes,
    # thin contours and small isolated color fields without exploding color count.
    detail_budget = min(6, max(2, max_colors // 4))
    for rgb in _edge_detail_colors(analysis, detail_budget, cancelled=cancelled):
        if len(custom) >= max_colors:
            break
        nearest = min(float(delta_e2000(rgb, p)) for p in fallback)
        if nearest < 2.0:
            continue
        if any(float(delta_e2000(rgb, old)) < 2.0 for old in custom):
            continue
        custom.append(rgb); custom_cov.append(0.0)

    custom = custom[:max_colors]
    custom_cov = custom_cov[:len(custom)]
    all_colors = _dedupe([*custom, *palette_colors], threshold=3)[:max_colors]
    result = PicturePalette(
        image_fp, str(calibration_fingerprint or ""), tuple(map(int, image.size)), max_colors, fidelity,
        tuple(all_colors), tuple(custom), tuple(palette_colors), tuple(custom_cov), False,
    )
    save_palette(result)
    return result


def apply_custom_rgb_sequence(mouse, keyboard_backend, controls: dict,
                              colors: Iterable[Sequence[int]], *, cancelled=lambda: False,
                              wait=time.sleep, progress=None) -> int:
    """Type a bounded RGB sequence into Paint's calibrated Edit colors dialog."""
    required = ("OpenCustomColor", "RedField", "GreenField", "BlueField", "ConfirmColor")
    missing = [name for name in required if name not in controls]
    if missing:
        raise ValueError("Numeric Paint RGB controls are not calibrated: " + ", ".join(missing))
    values = tuple(_rgb(c) for c in colors)
    dialog_open = False
    completed = 0

    def click(name: str, delay: float = 0.04) -> None:
        point = tuple(map(int, controls[name]))
        mouse.move(*point)
        wait(0.015)
        mouse.click()
        wait(delay)

    mouse.arm_input()
    try:
        for index, rgb in enumerate(values, 1):
            if cancelled():
                raise InterruptedError("Picture custom palette cancelled.")
            click("OpenCustomColor", 0.16)
            dialog_open = True
            for name, value in zip(("RedField", "GreenField", "BlueField"), rgb):
                if cancelled():
                    raise InterruptedError("Picture custom palette cancelled.")
                click(name, 0.025)
                keyboard_backend.press_and_release("ctrl+a")
                keyboard_backend.write(str(int(value)), delay=0.01)
                wait(0.025)
            click("ConfirmColor", 0.12)
            dialog_open = False
            completed += 1
            if progress is not None:
                progress(index, len(values), rgb)
    finally:
        if dialog_open:
            try:
                keyboard_backend.press_and_release("esc")
                wait(0.04)
            except Exception:
                pass
        mouse.disarm_input()
    return completed


def _resolve_max_colors(app) -> int:
    from DynamicColors import resolve_exact_color_limit
    setting = getattr(getattr(app, "exact_color_limit", None), "get", lambda: "Auto")()
    quality = getattr(getattr(app, "draw_quality", None), "get", lambda: "High likeness")()
    return max(1, min(32, int(resolve_exact_color_limit(setting, draw_quality=quality, preview=False))))


def _resolve_target(app, cancelled=lambda: False):
    target = getattr(app, "target_window", None)
    if target and len(target) >= 2:
        return int(target[0]), tuple(map(int, target[1]))
    from BrowserOneClick import _enumerate_windows
    from PaintPreparation import ensure_paint
    candidate = ensure_paint(_enumerate_windows, cancelled=cancelled,
                             wait=getattr(getattr(app, "stop", None), "wait", time.sleep))
    return int(candidate["handle"]), tuple(map(int, candidate["rect"]))


def start_picture_custom_palette(app) -> bool:
    """UI entry point for the Microsoft Paint picture-palette button."""
    if getattr(app, "activity", None) or getattr(app, "closing", False):
        return False
    profile = getattr(getattr(app, "game", None), "get", lambda: "")()
    if profile != "Microsoft Paint":
        app.status.set("Custom color palette for picture is available only for Microsoft Paint.")
        return False
    source = getattr(app, "original", None)
    if source is None:
        app.status.set("Load an image first, then build Custom color palette for picture.")
        return False
    try:
        single_color=bool(getattr(app,"paint_simple",None) and app.paint_simple.get())
    except Exception:
        single_color=False
    try:
        black_sketch=bool(getattr(app,"outline",None) and app.outline.get())
    except Exception:
        black_sketch=False
    try:
        eraser=bool(getattr(app,"paint_tool",None) and app.paint_tool.get()=="Eraser")
    except Exception:
        eraser=False
    if single_color or black_sketch or eraser:
        mode=("Single-color sketch/current ink" if single_color else ("Black contour sketch" if black_sketch else "Eraser"))
        app.status.set(f"{mode} does not need custom RGB colors. Edit colors will not be opened.")
        return False

    source_id = id(source)
    max_colors = _resolve_max_colors(app)
    fidelity = getattr(getattr(app, "color_fidelity", None), "get", lambda: "Faithful")()
    palette_path = getattr(app, "calibration_path", None)

    def work():
        if getattr(app, "stop", None) is not None and app.stop.is_set():
            raise InterruptedError("Picture custom palette cancelled.")
        # Resolve Paint and its RGB controls before fingerprinting the palette.
        # If this is the first run, the exact-color calibration file is created
        # below; the resulting fingerprint therefore stays reusable on later runs.
        handle, rect = _resolve_target(app, app.stop.is_set)
        from ScreenGuard import WindowMonitor
        monitor = WindowMonitor()
        target = (handle, rect)
        if not monitor.activate(target):
            raise ValueError("Windows could not activate Paint for picture custom palette preparation.")
        if app.stop.wait(0.20):
            raise InterruptedError("Picture custom palette cancelled.")
        from TargetCapture import probe_handle_isolated
        meta = probe_handle_isolated(handle)
        from ExactColorTools import numeric_rgb_available, resolved_controls, save as save_exact_colors
        if not numeric_rgb_available(PROFILE_KEY):
            # This is deliberately independent from full Paint canvas detection.
            # A clipped/zoomed canvas must not prevent exact RGB calibration.
            from PaintPreparation import prepare_controls
            from CalibrationAnchors import make_anchor
            app.events.put(("status", "Custom color palette for picture: calibrating Paint Edit colors R/G/B controls…"))
            exact_controls = prepare_controls(handle, cancelled=app.stop.is_set)
            meta = probe_handle_isolated(handle)
            save_exact_colors(PROFILE_KEY, exact_controls, anchor=make_anchor(tuple(meta["client_rect"])))
        controls = resolved_controls(PROFILE_KEY, tuple(meta["client_rect"]))
        try:
            from ProfileStorage import calibration_context_fingerprint
            calibration_fp = calibration_context_fingerprint(
                PROFILE_KEY, workflow="picture-custom-palette", palette_path=palette_path,
                extras=(f"colors:{max_colors}", f"fidelity:{fidelity}"),
            )
        except Exception:
            calibration_fp = ""
        from Colors import allColors
        fallback = tuple(tuple(c.RGB) for c in allColors)
        palette = build_picture_palette(
            source, fallback, max_colors=max_colors, fidelity=fidelity,
            calibration_fingerprint=calibration_fp, cancelled=app.stop.is_set,
        )
        if id(getattr(app, "original", None)) != source_id:
            raise InterruptedError("Source image changed while the picture palette was being prepared.")
        custom = tuple(palette.custom_colors)
        if not custom:
            app.picture_custom_palette_state = dict(palette.as_dict(), image_id=source_id, prepared_count=0)
            app.events.put(("status", f"Picture palette saved: {len(palette.colors)} colors are already covered by the calibrated Paint palette; no custom RGB entries were needed."))
            return
        from WindowsMouse import WindowsMouse
        mouse = WindowsMouse()
        keyboard_backend = getattr(app, "keyboard", None)
        if keyboard_backend is None:
            import keyboard as keyboard_backend

        def progress(index, total, rgb):
            # OK normally returns foreground ownership to Paint immediately, but
            # current XAML Paint can leave Edit colors visible for another UI
            # cycle. Give it a short cheap foreground grace period; only if the
            # modal persists do we use the calibrated/UIA OK fallback.
            active=False
            for _ in range(8):
                try:
                    if monitor.active(target):active=True;break
                except (OSError,ValueError,InterruptedError):
                    pass
                if app.stop.wait(.04):raise InterruptedError("Picture custom palette cancelled.")
            if not active:
                from PaintPreparation import close_edit_colors
                close_edit_colors(handle,accept=True,cancelled=app.stop.is_set,wait=app.stop.wait)
                if not monitor.activate(target):
                    raise InterruptedError("Paint Edit colors did not return focus to the Paint document.")
                if app.stop.wait(.12):raise InterruptedError("Picture custom palette cancelled.")
            app.events.put(("status", f"Custom color palette for picture: RGB {rgb} · {index}/{total}"))

        completed = apply_custom_rgb_sequence(
            mouse, keyboard_backend, controls, custom,
            cancelled=app.stop.is_set, wait=app.stop.wait, progress=progress,
        )
        # Hard postcondition for the preparation action: never leave Edit colors
        # over the document when control returns to Draw Studio.
        from PaintPreparation import close_edit_colors
        close_edit_colors(handle,accept=True,cancelled=app.stop.is_set,wait=app.stop.wait)
        if not monitor.activate(target):
            raise InterruptedError("Paint could not be reactivated after picture custom palette preparation.")
        if app.stop.wait(.12):raise InterruptedError("Picture custom palette cancelled.")
        app.picture_custom_palette_state = dict(
            palette.as_dict(), image_id=source_id, prepared_count=completed,
            cache_file=str(cache_path(palette.image_fingerprint, palette.calibration_fingerprint)),
        )
        # Seed only the method preference, never a fake verification result.
        # Runtime still performs its normal first-stroke color verification.
        try:
            from AdaptiveColor import rgb_key
            session = getattr(app, 'color_session_cache', None)
            if isinstance(session, dict):
                for rgb in custom:
                    session[rgb_key(rgb)] = {
                        'method':'numeric', 'confidence':0.0, 'actual':(), 'sample':None,
                        'prepared_picture_palette':True,
                    }
        except Exception:
            pass
        app.events.put((
            "status",
            f"Picture custom palette ready: {completed} custom RGB colors entered in Paint and {len(palette.palette_colors)} standard palette colors reused. The picture palette is saved for this image/calibration.",
        ))

    app.status.set(f"Building picture custom palette: analyzing image and preparing up to {max_colors} colors…")
    return bool(app.begin_worker("exact-color-calibration", work))
