"""Measured/calibrated draw-time estimates for Draw Studio.

v1.0.119 keeps the planner's operation timing model, then—when available—uses
completed local runtime samples to correct the estimate for the actual machine,
profile, browser and input cadence. No network/telemetry is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DrawTimeEstimate:
    preview_seconds: float
    projected_seconds: float
    low_seconds: float
    high_seconds: float
    confidence: str
    multiplier: float
    is_projection: bool
    reason: str
    estimate_source: str = "operation timing model"
    measured_samples: int = 0
    calibration_ratio: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "preview_seconds": round(float(self.preview_seconds), 3),
            "projected_seconds": round(float(self.projected_seconds), 3),
            "low_seconds": round(float(self.low_seconds), 3),
            "high_seconds": round(float(self.high_seconds), 3),
            "confidence": self.confidence,
            "multiplier": round(float(self.multiplier), 4),
            "is_projection": bool(self.is_projection),
            "reason": self.reason,
            "estimate_source": self.estimate_source,
            "measured_samples": int(self.measured_samples),
            "calibration_ratio": round(float(self.calibration_ratio), 4),
            "preview_label": format_duration(self.preview_seconds),
            "projected_label": format_duration(self.projected_seconds),
            "range_label": format_range(self.low_seconds, self.high_seconds),
        }


def _area(value: Any) -> tuple[int, int] | None:
    try:
        w, h = int(value[0]), int(value[1])
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return w, h


def format_duration(seconds: float) -> str:
    seconds = max(0.0, float(seconds or 0.0))
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    rem = int(round(seconds - minutes * 60))
    if rem >= 60:
        minutes += 1
        rem -= 60
    if minutes < 60:
        return f"{minutes}m {rem:02d}s" if rem else f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins:02d}m" if mins else f"{hours}h"


def format_range(low_seconds: float, high_seconds: float) -> str:
    low = max(0.0, float(low_seconds or 0.0))
    high = max(low, float(high_seconds or low))
    if abs(high - low) < 1.0:
        return format_duration(high)
    return f"{format_duration(low)}–{format_duration(high)}"


def _projection_exponent(options: dict[str, Any], path_stats: dict[str, Any]) -> tuple[float, str]:
    quality = str(options.get("draw_quality") or "")
    mode = str(path_stats.get("mode") or options.get("drawing_mode") or "")
    if "Pixel Accurate" in quality or path_stats.get("pixelmap"):
        return 1.00, "pixel-accurate area scaling"
    if mode == "Shape paths" or path_stats.get("shape_model"):
        return 0.56, "component/path scaling"
    if path_stats.get("joined_strokes"):
        return 0.64, "continuous-path scaling"
    return 0.70, "stroke-density scaling"


def _local_calibration(options: dict[str, Any]) -> dict[str, Any]:
    try:
        from DrawTimeCalibration import correction_for
        return correction_for(options)
    except Exception:
        return {"learned": False, "samples": 0, "ratio": 1.0, "mape": None}


def _measured_throughput_floor(plan: dict[str, Any], seconds: float) -> tuple[float, int]:
    """Use only genuinely learned Real-Speed history, never fallback PPS guesses."""
    options = plan.get("options") if isinstance(plan.get("options"), dict) else {}
    key = str(options.get("profile_key") or "").lower()
    try:
        from RealSpeedBudget import load_profile
        stored = load_profile(key)
        if not stored or int(stored.get("samples") or 0) <= 0:
            return seconds, 0
        pps = float(stored.get("paths_per_second") or 0.0)
        if pps <= 0:
            return seconds, 0
        count = max(0, int(plan.get("count") or 0))
        # operation_overhead_seconds excludes normal stroke paths and therefore
        # can safely be added to measured path throughput.
        overhead = max(0.0, float(plan.get("operation_overhead_seconds") or 0.0))
        measured = count / pps + overhead
        return max(seconds, measured), int(stored.get("samples") or 0)
    except Exception:
        return seconds, 0


def _measured_operation_floor(plan: dict[str, Any], calibration: dict[str, Any], seconds: float) -> tuple[float, int]:
    options=plan.get("options") if isinstance(plan.get("options"),dict) else {}
    meta=options.get("adaptive_deadline_meta") or {}
    counts=meta.get("operation_counts") or {}
    runtime=calibration.get("operation_runtime") or {}
    measured=0.0; matched=0
    for kind,count in counts.items():
        item=runtime.get(str(kind)) if isinstance(runtime,dict) else None
        if not isinstance(item,dict):continue
        try:
            avg=max(0.0,float(item.get("average_seconds") or 0.0)); n=max(0,int(count or 0))
        except Exception:continue
        if avg>0 and n>0:
            measured += avg*n; matched += n
    if matched:
        fixed=meta.get("fixed_overhead") or {}
        # Runtime path measurements start after countdown. Add non-path setup
        # that is not already represented by measured palette/tool operations.
        measured += max(0.0,float(fixed.get("countdown_seconds",3.0) or 0.0))
        measured += max(0.0,float(fixed.get("clear_seconds",0.0) or 0.0))
        measured += max(0.0,float(fixed.get("fill_seconds",0.0) or 0.0))
        return max(float(seconds or 0.0),measured),matched
    return float(seconds or 0.0),0


def _apply_measured_correction(plan: dict[str, Any], seconds: float) -> tuple[float, str, int, float, float | None]:
    options = plan.get("options") if isinstance(plan.get("options"), dict) else {}
    base, speed_samples = _measured_throughput_floor(plan, seconds)
    cal = _local_calibration(options)
    base, operation_samples = _measured_operation_floor(plan,cal,base)
    samples = int(cal.get("samples") or 0)
    ratio = float(cal.get("ratio") or 1.0)
    # Cold-start guard: the old operation model was consistently optimistic on
    # real browser input. Until this exact isolated profile has three completed
    # draws, never present raw theoretical timing as machine-calibrated truth.
    if samples <= 0:
        guard = 1.12 if speed_samples else 1.28
        corrected = base * guard
        source = (f"measured path throughput + cold-start guard ({speed_samples} sample{'s' if speed_samples != 1 else ''})"
                  if speed_samples else "conservative operation model; waiting for 3 completed draws")
        effective_ratio=guard
    elif samples == 1:
        effective_ratio=max(1.18,ratio)
        corrected=base*effective_ratio
        source="learning calibration (1/3 completed draws; conservative floor)"
    elif samples == 2:
        effective_ratio=max(1.08,ratio)
        corrected=base*effective_ratio
        source="learning calibration (2/3 completed draws; conservative floor)"
    else:
        effective_ratio=ratio
        corrected=base*effective_ratio
        source=f"measured local calibration ({samples} completed draws)"
    if operation_samples:
        source += f" + typed operation floor ({operation_samples} ops)"
    mape = cal.get("mape")
    try:
        mape = float(mape) if mape is not None else None
    except Exception:
        mape = None
    return max(0.0, corrected), source, samples, effective_ratio, mape


def _range_for(seconds: float, *, projection: bool, samples: int, mape: float | None) -> tuple[float, float, str]:
    seconds=max(0.0,float(seconds or 0.0))
    if samples >= 5:
        spread = max(.04, min(.22, float(mape if mape is not None else .10)))
        return max(0.0,seconds*(1-spread)), seconds*(1+spread), "high"
    if samples >= 3:
        spread=max(.06,min(.25,float(mape if mape is not None else .12)))
        return max(0.0,seconds*(1-spread)),seconds*(1+spread),"measured"
    if samples == 2:
        return seconds*.92, seconds*1.18, "learning"
    if samples == 1:
        return seconds*.90, seconds*1.24, "learning"
    # Asymmetric cold-start range: avoid a falsely precise number before real
    # mouse/browser timing exists. Projection uncertainty is wider still.
    return seconds*(.88 if not projection else .82), seconds*(1.28 if not projection else 1.38), "cold-start"


def estimate_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Return visible estimate metadata for a plan.

    The estimate is never randomized. It is derived from the exact planned
    operations/delays, optional measured path throughput, and a locally learned
    actual/predicted ratio from completed drawings.
    """
    options = plan.get("options") if isinstance(plan.get("options"), dict) else {}
    path_stats = plan.get("path_stats") if isinstance(plan.get("path_stats"), dict) else {}
    raw_preview_seconds = max(0.0, float(plan.get("estimate") or 0.0))
    preview_area = _area(plan.get("preview_area") or options.get("_preview_area") or plan.get("plan_area"))
    target_area = _area(plan.get("target_area") or options.get("_target_area") or plan.get("plan_area") or preview_area)

    is_projection = bool(preview_area and target_area and tuple(preview_area) != tuple(target_area) and not plan.get("full_detail_preview"))
    reason = "native/full-detail operation plan"
    multiplier = 1.0
    projected_raw = raw_preview_seconds
    if is_projection:
        p_area = max(1, preview_area[0] * preview_area[1])
        t_area = max(1, target_area[0] * target_area[1])
        area_ratio = max(1.0, t_area / p_area)
        exponent, reason = _projection_exponent(options, path_stats)
        multiplier = min(24.0, max(1.0, area_ratio ** exponent))
        projected_raw = raw_preview_seconds * multiplier
        # Planning/setup overhead does not scale with image area.
        projected_raw += 6.0 + min(60.0, float(len(plan.get("groups") or ())) * .22)

    corrected, source, samples, ratio, mape = _apply_measured_correction(plan, projected_raw)
    low, high, confidence = _range_for(corrected, projection=is_projection, samples=samples, mape=mape)
    return DrawTimeEstimate(
        preview_seconds=raw_preview_seconds,
        projected_seconds=corrected,
        low_seconds=low,
        high_seconds=high,
        confidence=confidence,
        multiplier=multiplier,
        is_projection=is_projection,
        reason=reason,
        estimate_source=source,
        measured_samples=samples,
        calibration_ratio=ratio,
    ).as_dict()


def attach_draw_time_estimate(plan: dict[str, Any]) -> dict[str, Any]:
    meta = estimate_from_plan(plan)
    plan["draw_time_estimate"] = meta
    return meta


def record_completed_draw(plan: dict[str, Any], actual_seconds: float, *, completed_paths: int = 0) -> dict[str, Any]:
    """Teach the local estimate from one clean, completed real draw."""
    try:
        from DrawTimeCalibration import record_sample
        options = plan.get("options") if isinstance(plan.get("options"), dict) else {}
        predicted = max(0.0, float(plan.get("raw_execution_estimate_seconds") or plan.get("estimate") or 0.0))
        fill_actions = len(options.get("fill_regions") or ()) + (1 if (options.get("background_fill_plan") or {}).get("enabled") else 0)
        operation_counts=(options.get('adaptive_deadline_meta') or {}).get('operation_counts') or {}
        operation_runtime=options.get('runtime_operation_timing') or {}
        return record_sample(options, predicted, actual_seconds, completed_paths=completed_paths, fill_actions=fill_actions,
                             operation_counts=operation_counts, operation_runtime=operation_runtime)
    except Exception as error:
        return {"recorded": False, "reason": str(error)}


def status_line(plan: dict[str, Any]) -> str:
    meta = plan.get("draw_time_estimate") or estimate_from_plan(plan)
    prefix = "Estimated final draw time" if meta.get("is_projection") else "Estimated draw time"
    label = meta.get("projected_label") or format_duration(meta.get("projected_seconds", 0))
    source = str(meta.get("estimate_source") or "")
    if meta.get("is_projection"):
        return f"{prefix}: about {label} ({meta.get('range_label')}, {meta.get('confidence')} confidence; {source})."
    if int(meta.get("measured_samples") or 0) > 0:
        return f"{prefix}: about {label} ({meta.get('range_label')}, {meta.get('confidence')} confidence; {source})."
    return f"{prefix}: about {label} ({source})."
