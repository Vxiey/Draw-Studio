"""Step 13 — real-result verification from a safe final canvas snapshot.

This module contains only deterministic, local, read-only scoring helpers.  The
execution layer may pass a freshly captured canvas image, but this module never
writes image bytes, screenshots, crops, hashes or thumbnails to disk.  Returned
metadata is limited to compact numeric scores and trust/reason flags.
"""
from __future__ import annotations

from typing import Any
import math
import numpy as np
from PIL import Image

from AccuracyEvaluator import evaluate_preview, normalize_source

BACKGROUND_RGB = (255, 255, 255)
_SAFE_STATES = {"verified", "scored", "low-trust", "unavailable"}


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def _int_tuple2(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    try:
        a, b = value
        return max(1, int(round(float(a)))), max(1, int(round(float(b))))
    except Exception:
        return default


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _rgb_array(image: Image.Image, size: tuple[int, int] | None = None) -> np.ndarray:
    im = image.convert("RGB")
    if size is not None and im.size != tuple(size):
        im = im.resize(tuple(size), Image.Resampling.LANCZOS)
    return np.asarray(im, dtype=np.int16)


def _foreground_mask(image: Image.Image, *, background: tuple[int, int, int] = BACKGROUND_RGB,
                     threshold: int = 18) -> np.ndarray:
    arr = _rgb_array(image)
    bg = np.asarray(background, dtype=np.int16).reshape(1, 1, 3)
    return np.max(np.abs(arr - bg), axis=2) > int(threshold)


def _mask_stats(expected: np.ndarray, actual: np.ndarray) -> dict[str, float | int]:
    expected = np.asarray(expected, dtype=bool)
    actual = np.asarray(actual, dtype=bool)
    expected_count = int(np.count_nonzero(expected))
    actual_count = int(np.count_nonzero(actual))
    overlap = int(np.count_nonzero(expected & actual))
    unexpected = int(np.count_nonzero(actual & ~expected))
    missed = int(np.count_nonzero(expected & ~actual))
    return {
        "expected_foreground_pixels": expected_count,
        "actual_foreground_pixels": actual_count,
        "foreground_overlap_pixels": overlap,
        "missed_foreground_pixels": missed,
        "unexpected_foreground_pixels": unexpected,
        "actual_coverage_percent": 100.0 if expected_count <= 0 else round(overlap * 100.0 / expected_count, 3),
        "unexpected_ink_percent": 0.0 if actual_count <= 0 else round(unexpected * 100.0 / actual_count, 3),
        "blank_canvas": bool(actual_count <= max(2, expected.size // 2500)),
    }


def _trust_from_scores(*, profile_key: str, visual: float | None, simulated_match: float | None,
                       actual_coverage: float | None, unexpected_ink: float | None,
                       expected_foreground: int, blank_canvas: bool,
                       geometry_ok: bool, deadline_safe: bool | None,
                       source_size_ok: bool) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    confidence = 100.0

    if not geometry_ok:
        reasons.append("capture-geometry-uncertain")
        confidence -= 35.0
    if not source_size_ok:
        reasons.append("source-size-normalized")
        confidence -= 6.0
    if expected_foreground > 0 and blank_canvas:
        reasons.append("blank-or-nearly-blank-canvas")
        confidence -= 55.0
    if actual_coverage is not None and actual_coverage < 55.0 and expected_foreground > 0:
        reasons.append("low-actual-coverage")
        confidence -= 25.0
    if unexpected_ink is not None and unexpected_ink > 35.0:
        reasons.append("unexpected-ink-outside-plan")
        confidence -= 18.0
    if simulated_match is not None and simulated_match < 62.0:
        reasons.append("actual-canvas-differs-from-simulated-final")
        confidence -= 22.0
    if visual is not None and visual < 45.0:
        reasons.append("very-low-source-visual-accuracy")
        confidence -= 10.0
    if deadline_safe is False:
        reasons.append("deadline-ended-tight-or-over-budget")
        confidence -= 12.0

    confidence = _clamp(confidence, 0.0, 100.0)
    if confidence >= 82.0 and not reasons:
        return "high", confidence, reasons
    if confidence >= 68.0 and "blank-or-nearly-blank-canvas" not in reasons:
        return "medium", confidence, reasons
    if confidence >= 35.0:
        return "low", confidence, reasons
    return "none", confidence, reasons


def crop_fitted_canvas(snapshot: Image.Image, *, area: tuple[int, int, int, int],
                       fitted: tuple[float, float]) -> tuple[Image.Image, dict[str, Any]]:
    """Crop the actually drawn fitted frame from a full selected-canvas capture.

    ``area`` is the selected canvas rectangle in screen coordinates as
    ``(left, top, width, height)``.  ``snapshot`` is expected to be a read-only
    capture of that selected canvas.  DPI/window scaling is handled by measuring
    snapshot pixels relative to the selected area.
    """
    if not isinstance(snapshot, Image.Image):
        raise TypeError("snapshot must be a PIL Image")
    if snapshot.width < 2 or snapshot.height < 2:
        raise ValueError("snapshot image is too small")
    ax, ay, aw, ah = area
    aw = max(1.0, float(aw)); ah = max(1.0, float(ah))
    fw, fh = fitted
    fw = _clamp(_float(fw, aw) or aw, 1.0, aw)
    fh = _clamp(_float(fh, ah) or ah, 1.0, ah)
    scale_x = float(snapshot.width) / aw
    scale_y = float(snapshot.height) / ah
    inset_x = (aw - fw) * 0.5
    inset_y = (ah - fh) * 0.5
    x0 = max(0, int(round(inset_x * scale_x)))
    y0 = max(0, int(round(inset_y * scale_y)))
    x1 = min(snapshot.width, int(round((inset_x + fw) * scale_x)))
    y1 = min(snapshot.height, int(round((inset_y + fh) * scale_y)))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("fitted canvas crop is empty")
    geometry_ok = (x1 - x0) >= 2 and (y1 - y0) >= 2 and 0.25 <= scale_x / max(1e-9, scale_y) <= 4.0
    meta = {
        "crop_box": (int(x0), int(y0), int(x1), int(y1)),
        "capture_size": (int(snapshot.width), int(snapshot.height)),
        "drawn_crop_size": (int(x1 - x0), int(y1 - y0)),
        "selected_area_size": (int(round(aw)), int(round(ah))),
        "fitted_size": (int(round(fw)), int(round(fh))),
        "scale_x": round(scale_x, 5),
        "scale_y": round(scale_y, 5),
        "geometry_ok": bool(geometry_ok),
    }
    return snapshot.convert("RGB").crop((x0, y0, x1, y1)), meta


def score_final_canvas_snapshot(*, snapshot: Image.Image, original_source: Image.Image,
                                area: tuple[int, int, int, int], fitted: tuple[float, float],
                                comparison_size: tuple[int, int] | None = None,
                                simulated_final: Image.Image | None = None,
                                quantized_target: Image.Image | None = None,
                                profile_key: str = "",
                                actual_elapsed_seconds: float | None = None,
                                usable_deadline_seconds: float | None = None,
                                visual_gate_percent: float | None = None,
                                background: tuple[int, int, int] = BACKGROUND_RGB) -> dict[str, Any]:
    """Score a finished real drawing from a temporary canvas snapshot.

    The caller owns the screenshot/crop lifetime.  This function returns only
    numeric metrics and reason strings; it never stores or returns images.
    """
    if not isinstance(original_source, Image.Image):
        return {"available": False, "trusted": False, "feedback_trust": "none", "scoring_state": "unavailable", "reason": "missing original source", "capture_pixels_persisted": False}
    try:
        crop, geometry = crop_fitted_canvas(snapshot, area=tuple(area), fitted=tuple(fitted))
        if comparison_size is None:
            if isinstance(simulated_final, Image.Image):
                comparison_size = simulated_final.size
            else:
                comparison_size = _int_tuple2(getattr(original_source, "size", None), (max(1, crop.width), max(1, crop.height)))
        comparison_size = _int_tuple2(comparison_size, (max(1, crop.width), max(1, crop.height)))
        actual = crop.resize(comparison_size, Image.Resampling.LANCZOS).convert("RGB")
        source_norm = normalize_source(original_source, comparison_size, background=background)
        source_size_ok = bool(getattr(source_norm, "size", None) == comparison_size)

        expected_image = simulated_final if isinstance(simulated_final, Image.Image) else source_norm
        expected_norm = expected_image.convert("RGB")
        if expected_norm.size != comparison_size:
            expected_norm = expected_norm.resize(comparison_size, Image.Resampling.LANCZOS)
        expected_mask = _foreground_mask(expected_norm, background=background)
        actual_mask = _foreground_mask(actual, background=background)
        mask = _mask_stats(expected_mask, actual_mask)
        actual_coverage = float(mask["actual_coverage_percent"])

        source_metrics = evaluate_preview(source_norm, actual, coverage_percent=actual_coverage,
                                          return_error_map=False, return_delta_e_heatmap=False)
        simulated_match = None
        simulated_metrics: dict[str, Any] = {}
        if isinstance(simulated_final, Image.Image):
            simulated_norm = simulated_final.convert("RGB")
            if simulated_norm.size != comparison_size:
                simulated_norm = simulated_norm.resize(comparison_size, Image.Resampling.LANCZOS)
            simulated_metrics = evaluate_preview(simulated_norm, actual, coverage_percent=actual_coverage,
                                                 return_error_map=False, return_delta_e_heatmap=False)
            simulated_match = _float(simulated_metrics.get("visual_accuracy_percent"), None)
        target_match = None
        if isinstance(quantized_target, Image.Image):
            target_norm = quantized_target.convert("RGB")
            if target_norm.size != comparison_size:
                target_norm = target_norm.resize(comparison_size, Image.Resampling.LANCZOS)
            target_metrics = evaluate_preview(target_norm, actual, coverage_percent=actual_coverage,
                                              return_error_map=False, return_delta_e_heatmap=False)
            target_match = _float(target_metrics.get("visual_accuracy_percent"), None)
        else:
            target_metrics = None

        elapsed = _float(actual_elapsed_seconds, None)
        usable = _float(usable_deadline_seconds, None)
        deadline_safe = None if usable is None or elapsed is None else elapsed <= usable - 0.25
        visual = _float(source_metrics.get("visual_accuracy_percent"), None)
        gate = _float(visual_gate_percent, None)
        gate_passed = None if gate is None or visual is None else visual + 1e-9 >= gate
        trust, confidence, reasons = _trust_from_scores(
            profile_key=str(profile_key or ""), visual=visual, simulated_match=simulated_match,
            actual_coverage=actual_coverage, unexpected_ink=_float(mask.get("unexpected_ink_percent"), 0.0),
            expected_foreground=int(mask.get("expected_foreground_pixels") or 0),
            blank_canvas=bool(mask.get("blank_canvas")), geometry_ok=bool(geometry.get("geometry_ok")),
            deadline_safe=deadline_safe, source_size_ok=source_size_ok)
        trusted = trust in ("high", "medium")
        state = "verified" if trusted else ("low-trust" if trust == "low" else "unavailable")
        delta = source_metrics.get("delta_e_oklab") if isinstance(source_metrics.get("delta_e_oklab"), dict) else {}
        meta: dict[str, Any] = {
            "available": True,
            "trusted": bool(trusted),
            "feedback_trust": trust,
            "scoring_state": state if state in _SAFE_STATES else "low-trust",
            "confidence_percent": round(confidence, 2),
            "reasons": tuple(reasons),
            "evidence": "safe read-only final canvas snapshot",
            "method": "actual final canvas snapshot vs original source; local in-memory OKLab evaluation; no image pixels persisted",
            "capture_pixels_persisted": False,
            "image_pixels_persisted": False,
            "stores_image_data": False,
            "privacy": "Only compact metrics and trust flags are kept; canvas/source pixels, screenshots, crops, hashes and thumbnails are discarded.",
            "comparison_size": tuple(map(int, comparison_size)),
            "capture_size": tuple(map(int, geometry["capture_size"])),
            "drawn_crop_size": tuple(map(int, geometry["drawn_crop_size"])),
            "selected_area_size": tuple(map(int, geometry["selected_area_size"])),
            "fitted_size": tuple(map(int, geometry["fitted_size"])),
            "geometry_ok": bool(geometry.get("geometry_ok")),
            "actual_coverage_percent": round(actual_coverage, 2),
            "unexpected_ink_percent": round(float(mask.get("unexpected_ink_percent") or 0.0), 2),
            "expected_foreground_pixels": int(mask.get("expected_foreground_pixels") or 0),
            "actual_foreground_pixels": int(mask.get("actual_foreground_pixels") or 0),
            "blank_canvas": bool(mask.get("blank_canvas")),
            "visual_accuracy_percent": source_metrics.get("visual_accuracy_percent"),
            "source_pixel_accuracy_percent": source_metrics.get("source_pixel_accuracy_percent"),
            "perceptual_color_accuracy_percent": source_metrics.get("perceptual_color_accuracy_percent"),
            "luminance_accuracy_percent": source_metrics.get("luminance_accuracy_percent"),
            "hue_accuracy_percent": source_metrics.get("hue_accuracy_percent"),
            "edge_accuracy_percent": source_metrics.get("edge_accuracy_percent"),
            "delta_e_oklab": {
                "mean_delta_e_oklab": delta.get("mean_delta_e_oklab"),
                "p95_delta_e_oklab": delta.get("p95_delta_e_oklab"),
                "max_delta_e_oklab": delta.get("max_delta_e_oklab"),
                "severe_error_pixels_percent": delta.get("severe_error_pixels_percent"),
            },
            "actual_vs_simulated_visual_percent": None if simulated_match is None else round(float(simulated_match), 2),
            "actual_vs_simulated_source_pixel_percent": None if not simulated_metrics else simulated_metrics.get("source_pixel_accuracy_percent"),
            "actual_vs_quantized_target_visual_percent": None if target_match is None else round(float(target_match), 2),
            "visual_gate_percent": None if gate is None else round(gate, 2),
            "visual_gate_passed": gate_passed,
            "deadline_safe": deadline_safe,
            "actual_elapsed_seconds": None if elapsed is None else round(elapsed, 3),
            "usable_deadline_seconds": None if usable is None else round(usable, 3),
        }
        if not reasons and trusted:
            meta["summary"] = "Real result verified from final canvas snapshot."
        elif trust == "low":
            meta["summary"] = "Real result snapshot scored with low trust: " + ", ".join(reasons[:3])
        elif not trusted:
            meta["summary"] = "Real result snapshot was not trusted: " + ", ".join(reasons[:3])
        else:
            meta["summary"] = "Real result verified with notes: " + ", ".join(reasons[:3])
        return meta
    except Exception as error:
        return {
            "available": False,
            "trusted": False,
            "feedback_trust": "none",
            "scoring_state": "unavailable",
            "reason": str(error)[:240],
            "capture_pixels_persisted": False,
            "image_pixels_persisted": False,
            "stores_image_data": False,
            "privacy": "No screenshot or image pixels were saved.",
        }
