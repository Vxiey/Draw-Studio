"""Region Fill Engine for Image Draw Bot v1.0.119-beta.

This module deliberately builds on Image Draw Bot's existing conservative connected-
component/bucket-fill detector. It adds a second safety/cost layer and produces a
shared plan that preview and final execution can consume without guessing again.

The engine never sends input. It only plans. Runtime CanvasGuard and fill leak
verification remain authoritative during execution.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import ceil
from typing import Any, Iterable

from FillOptimizer import detect_fill_regions
from SpeedOptimizer import normalize_speed, phase_delay
from StrokeDelivery import resolve_stroke_delivery

AGGRESSIVENESS = ("Safe", "Balanced", "Aggressive")
QUALITY_PRESETS = ("Fast", "Balanced", "High Quality", "Pixel Accurate")


@dataclass(frozen=True)
class RegionDecision:
    region_id: int
    accepted: bool
    render_method: str
    fill_confidence: float
    leak_risk: float
    thin_neck_score: float
    stroke_cost_seconds: float
    fill_cost_seconds: float
    estimated_time_saved_seconds: float
    visual_error_cost: float
    seconds_saved_per_visual_error: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_quality(options: dict[str, Any]) -> str:
    if str(options.get("draw_quality") or "") == "Pixel Accurate":
        return "Pixel Accurate"
    if str(options.get("render_preset") or "") == "Extra fast" or normalize_speed(options.get("speed", "Balanced")) == "Fast":
        return "Fast"
    if str(options.get("draw_quality") or "") in ("Maximum likeness", "GPU enhanced"):
        return "High Quality"
    return "Balanced"


def _resolve_detector_mode(aggressiveness: str, quality: str) -> str:
    value = str(aggressiveness or "Balanced")
    if value not in AGGRESSIVENESS:
        value = "Balanced"
    if quality == "High Quality" and value == "Aggressive":
        return "Balanced"
    if quality == "Pixel Accurate":
        return "Conservative"
    return {"Safe": "Conservative", "Balanced": "Balanced", "Aggressive": "Aggressive"}[value]


def _candidate_cap(options: dict[str, Any], aggressiveness: str) -> int:
    # Bound memory/runtime while allowing far more fill regions than the legacy
    # 12-region cap. RAM budget may be supplied by ResourceAllocation.
    base = {"Safe": 128, "Balanced": 256, "Aggressive": 512}.get(aggressiveness, 256)
    try:
        ram = int(options.get("ram_budget_mb") or 512)
    except Exception:
        ram = 512
    if ram < 512:
        base = min(base, 96)
    elif ram < 1024:
        base = min(base, 192)
    return max(24, min(768, base))


def _span_widths(region: dict[str, Any]) -> list[int]:
    out = []
    for raw in region.get("row_spans") or ():
        try:
            _y, left, right = map(int, raw)
        except Exception:
            continue
        out.append(max(1, right - left + 1))
    return out


def _thin_neck_score(region: dict[str, Any], brush_px: int) -> float:
    widths = sorted(_span_widths(region))
    if not widths:
        return 1.0
    # A single one-pixel tip should not condemn a huge otherwise-safe component;
    # use the lower decile as a robust neck estimate.
    sample = widths[min(len(widths) - 1, max(0, int(len(widths) * .10)))]
    critical = max(2.0, float(brush_px) * 1.35)
    if sample >= critical * 2.25:
        return 0.0
    if sample <= critical:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (sample - critical) / (critical * 1.25)))


def _risk(region: dict[str, Any], *, aggressiveness: str, quality: str, brush_px: int) -> tuple[float, float, str]:
    safety = max(0.0, min(1.0, float(region.get("safety_score", 0.0) or 0.0)))
    density = max(0.0, min(1.0, float(region.get("bbox_density", 0.0) or 0.0)))
    area = max(1, int(region.get("area_pixels", 1) or 1))
    perimeter = max(1, int(region.get("perimeter_pixels", 1) or 1))
    contour = region.get("contour") or ()
    vertices = max(1, len(contour) - 1)
    thin = _thin_neck_score(region, brush_px)
    shape_pressure = min(1.0, perimeter / max(8.0, area ** .5 * 14.0))
    vertex_pressure = min(1.0, vertices / 160.0)
    low_density = max(0.0, 1.0 - density)

    # Detector has already hard-rejected holes, open/ambiguous contours and edge
    # touching components. This score is a second conservative layer.
    risk = (
        (1.0 - safety) * .46
        + thin * .24
        + shape_pressure * .12
        + vertex_pressure * .10
        + low_density * .08
    )
    if quality == "High Quality":
        risk *= 1.08
    elif quality == "Fast":
        risk *= .94
    risk = max(0.0, min(1.0, risk))
    confidence = 1.0 - risk

    limits = {"Safe": .14, "Balanced": .24, "Aggressive": .34}
    limit = limits.get(aggressiveness, .24)
    if quality == "High Quality":
        limit = min(limit, .20)
    if quality == "Pixel Accurate":
        limit = min(limit, .10)

    # Hard blockers stay hard regardless of aggressiveness.
    if not contour or len(contour) < 5:
        return 1.0, 0.0, "missing closed contour"
    if thin >= .98 and min(_span_widths(region) or [0]) <= max(1, brush_px):
        return 1.0, 0.0, "thin-neck hard blocker"
    if risk > limit:
        return risk, confidence, f"leak risk {risk:.2f} > {limit:.2f}"
    return risk, confidence, "safe"


def _region_cost(region: dict[str, Any], options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> tuple[float, float]:
    # Preserve the established safe-fill decision boundary on cold start.  The
    # calibrated model is allowed to change fill-vs-stroke selection only after
    # this exact profile/tool/brush/color workflow has real completed samples.
    from HybridCostModel import build_cost_model
    model = build_cost_model(options)
    if not model.calibrated:
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
        stroke_cost = 0.0
        for raw in region.get("row_spans") or ():
            try:
                _y, left, right = map(int, raw)
            except Exception:
                continue
            length = max(0.0, (right - left) * sx)
            moves = max(1, int(ceil(length / step)))
            stroke_cost += travel_delay + moves * path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
        perimeter = max(1.0, float(region.get("perimeter_pixels", 1) or 1))
        scaled_perimeter = perimeter * ((sx + sy) * .5)
        contour_moves = max(4, int(ceil(scaled_perimeter / step)))
        fill_cost = travel_delay + contour_moves * path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
        fill_cost += max(.08, delivery.ui_control_delay * .45) + .24
        return max(.001, stroke_cost), max(.001, fill_cost)

    iw, ih=max(1,int(image_size[0])),max(1,int(image_size[1]));fw,fh=max(1,int(fitted[0])),max(1,int(fitted[1]))
    sx,sy=fw/iw,fh/ih
    stroke_cost=0.0
    for raw in region.get("row_spans") or ():
        try:_y,left,right=map(int,raw)
        except Exception:continue
        stroke_cost+=model.distance_path_seconds(max(0.0,(right-left)*sx),travel_px=4.0)
    perimeter=max(1.0,float(region.get("perimeter_pixels",1) or 1))*((sx+sy)*.5)
    fill_cost=model.distance_path_seconds(perimeter,travel_px=4.0)+model.tool_change_seconds+model.fill_action_seconds+model.verification_seconds
    return max(.001,stroke_cost),max(.001,fill_cost)


def build_region_fill_plan(image, fitted: tuple[int, int], options: dict[str, Any], *, safe_margin_px: int = 0, cancelled=lambda: False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return accepted region dictionaries plus planner metadata.

    Pixel Accurate is intentionally protected in this first Region Fill Engine
    release. Its exact simulator currently models strokes, not a bucket-fill
    operation, so the engine refuses to substitute fill until exact fill
    simulation can prove pixel equivalence. This preserves the invariant that
    preview/final/error-map geometry cannot diverge.
    """
    quality = _resolve_quality(options)
    aggressiveness = str(options.get("fill_aggressiveness") or "Balanced")
    if aggressiveness not in AGGRESSIVENESS:
        aggressiveness = "Balanced"

    if quality == "Pixel Accurate":
        return [], {
            "enabled": True,
            "quality_preset": quality,
            "fill_aggressiveness": "Safe",
            "pixel_accurate_protected": True,
            "reason": "Pixel Accurate keeps the exact stroke simulator until bucket-fill simulation can prove exact equivalence.",
            "total_regions": 0,
            "fill_safe_regions": 0,
            "fill_actions": 0,
            "outline_paths": 0,
            "fallback_stroke_regions": 0,
            "fill_coverage_percent": 0.0,
            "estimated_time_saved_seconds": 0.0,
        }

    detector_mode = _resolve_detector_mode(aggressiveness, quality)
    cap = _candidate_cap(options, aggressiveness)
    regions, base_meta = detect_fill_regions(
        image,
        detector_mode,
        engine=options.get("fill_engine", "Auto"),
        max_regions=cap,
        cancelled=cancelled,
        return_meta=True,
        safe_margin_px=safe_margin_px,
    )
    decisions: list[RegionDecision] = []
    accepted: list[dict[str, Any]] = []
    rejected_cost = 0
    rejected_safety = 0
    brush_px = max(1, int(options.get("brush_px", 1) or 1))
    min_saving_ratio = {"Safe": .10, "Balanced": .04, "Aggressive": 0.0}[aggressiveness]
    deadline_active=bool(options.get("time_budget_active"))
    deadline_seconds=float(options.get("max_seconds",180) or 180)
    value_threshold={"Safe":2.0,"Balanced":1.0,"Aggressive":.35}[aggressiveness] if deadline_active and deadline_seconds<=90 else {"Safe":3.0,"Balanced":1.5,"Aggressive":.55}[aggressiveness]
    absolute_saving_floor=.08 if deadline_active and deadline_seconds<=90 else .12

    for idx, item in enumerate(regions):
        if cancelled():
            raise InterruptedError()
        region = item.as_dict() if hasattr(item, "as_dict") else dict(item)
        risk, confidence, safety_reason = _risk(
            region, aggressiveness=aggressiveness, quality=quality, brush_px=brush_px
        )
        stroke_cost, fill_cost = _region_cost(region, options, image.size, fitted)
        saving = max(0.0, stroke_cost - fill_cost)
        thin_score=_thin_neck_score(region, brush_px)
        visual_error=max(.005,min(1.0,risk*.62 + thin_score*.20 + (1.0-confidence)*.18))
        seconds_per_error=saving/max(.01,visual_error)
        cost_ok = fill_cost <= stroke_cost * (1.0 - min_saving_ratio)
        value_ok = saving >= absolute_saving_floor and seconds_per_error >= value_threshold
        safety_ok = safety_reason == "safe"
        accepted_here = bool(safety_ok and cost_ok and value_ok)
        reason = "safe and high time-saved/visual-error value"
        if not safety_ok:
            rejected_safety += 1
            reason = safety_reason
        elif not cost_ok:
            rejected_cost += 1
            reason = "stroke/run renderer is cheaper"
        elif not value_ok:
            rejected_cost += 1
            reason = f"fill saves too little for visual risk ({seconds_per_error:.2f}s/error)"

        decision = RegionDecision(
            region_id=idx,
            accepted=accepted_here,
            render_method="OUTLINE_FILL" if accepted_here else "HORIZONTAL_RUNS",
            fill_confidence=confidence,
            leak_risk=risk,
            thin_neck_score=thin_score,
            stroke_cost_seconds=stroke_cost,
            fill_cost_seconds=fill_cost,
            estimated_time_saved_seconds=saving if accepted_here else 0.0,
            visual_error_cost=visual_error,
            seconds_saved_per_visual_error=seconds_per_error,
            reason=reason,
        )
        decisions.append(decision)
        if accepted_here:
            region.update({
                "region_fill_id": idx,
                "render_method": "OUTLINE_FILL",
                "fill_confidence": round(confidence, 5),
                "leak_risk": round(risk, 5),
                "thin_neck_score": round(decision.thin_neck_score, 5),
                "stroke_cost_seconds": round(stroke_cost, 5),
                "fill_cost_seconds": round(fill_cost, 5),
                "estimated_time_saved_seconds": round(saving, 5),
                "visual_error_cost": round(visual_error, 6),
                "seconds_saved_per_visual_error": round(seconds_per_error, 4),
                "outline_simplification": "exact-collinear",
            })
            accepted.append(region)

    area = max(1, int(image.size[0]) * int(image.size[1]))
    accepted_pixels = sum(max(0, int(r.get("area_pixels", 0) or 0)) for r in accepted)
    saved_strokes = sum(max(0, int(r.get("estimated_saved_strokes", 0) or 0)) for r in accepted)
    total_time_saved = sum(float(r.get("estimated_time_saved_seconds", 0.0) or 0.0) for r in accepted)
    fill_colors = len({int(r.get("color_index", -1)) for r in accepted if int(r.get("color_index", -1)) >= 0})
    total_regions = int(base_meta.get("total_components", 0) or 0)
    fallback = max(0, total_regions - len(accepted))

    meta = dict(base_meta)
    meta.update({
        "enabled": True,
        "engine_name": "Region Fill Engine",
        "quality_preset": quality,
        "fill_aggressiveness": aggressiveness,
        "detector_mode": detector_mode,
        "candidate_cap": cap,
        "total_regions": total_regions,
        "fill_safe_regions": len(accepted),
        "fill_actions": len(accepted),
        "outline_paths": len(accepted),
        "fallback_stroke_regions": fallback,
        "rejected_by_cost": rejected_cost,
        "rejected_by_safety": rejected_safety,
        "fill_coverage_percent": round(accepted_pixels / area * 100.0, 3),
        "estimated_saved_strokes": saved_strokes,
        "estimated_time_saved_seconds": round(total_time_saved, 3),
        "fill_value_policy": "seconds_saved_per_visual_error",
        "fill_value_threshold": value_threshold,
        "fill_absolute_saving_floor_seconds": absolute_saving_floor,
        "average_seconds_saved_per_visual_error": round(sum(float(r.get("seconds_saved_per_visual_error",0) or 0) for r in accepted)/max(1,len(accepted)),3),
        "hybrid_cost_model": __import__('HybridCostModel').build_cost_model(options).as_dict(),
        "fill_color_batches": fill_colors,
        "outline_simplification": "exact-collinear only",
        "region_merging": "disabled here; existing palette/grouping policy remains authoritative",
        "pixel_accurate_protected": False,
        "decisions": [d.as_dict() for d in decisions[:80]],
        "decision_count": len(decisions),
    })
    return accepted, meta



def evaluate_region_candidates(regions, image_size: tuple[int, int], fitted: tuple[int, int], options: dict[str, Any], *,
                               base_meta: dict[str, Any] | None = None, cancelled=lambda: False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply Region Fill Engine safety/value policy to pre-detected regions.

    Extra Fast 2.0 uses this for Dynamic/Adaptive Exact groups whose color indexes
    belong to the plan-local palette.  Geometry detection is separate, but the
    same leak-risk, thin-neck and wall-clock value policy remains authoritative.
    """
    quality=_resolve_quality(options)
    aggressiveness=str(options.get('fill_aggressiveness') or 'Balanced')
    if aggressiveness not in AGGRESSIVENESS:aggressiveness='Balanced'
    if quality=='Pixel Accurate':
        return [],{'enabled':True,'quality_preset':quality,'fill_aggressiveness':'Safe','pixel_accurate_protected':True,
                   'reason':'Pixel Accurate keeps exact stroke simulation.','total_regions':0,'fill_safe_regions':0,
                   'fill_actions':0,'outline_paths':0,'fallback_stroke_regions':0,'fill_coverage_percent':0.0,
                   'estimated_time_saved_seconds':0.0}
    base_meta=dict(base_meta or {})
    decisions=[];accepted=[];rejected_cost=0;rejected_safety=0
    brush_px=max(1,int(options.get('brush_px',1) or 1))
    min_saving_ratio={'Safe':.10,'Balanced':.04,'Aggressive':0.0}[aggressiveness]
    deadline_active=bool(options.get('time_budget_active'))
    deadline_seconds=float(options.get('max_seconds',180) or 180)
    value_threshold=({'Safe':2.0,'Balanced':1.0,'Aggressive':.35} if deadline_active and deadline_seconds<=90 else {'Safe':3.0,'Balanced':1.5,'Aggressive':.55})[aggressiveness]
    absolute_saving_floor=.08 if deadline_active and deadline_seconds<=90 else .12
    for idx,item in enumerate(regions or ()):
        if cancelled():raise InterruptedError()
        region=item.as_dict() if hasattr(item,'as_dict') else dict(item)
        risk,confidence,safety_reason=_risk(region,aggressiveness=aggressiveness,quality=quality,brush_px=brush_px)
        stroke_cost,fill_cost=_region_cost(region,options,image_size,fitted)
        saving=max(0.0,stroke_cost-fill_cost);thin_score=_thin_neck_score(region,brush_px)
        visual_error=max(.005,min(1.0,risk*.62+thin_score*.20+(1.0-confidence)*.18))
        seconds_per_error=saving/max(.01,visual_error)
        cost_ok=fill_cost<=stroke_cost*(1.0-min_saving_ratio)
        value_ok=saving>=absolute_saving_floor and seconds_per_error>=value_threshold
        safety_ok=safety_reason=='safe';accepted_here=bool(safety_ok and cost_ok and value_ok)
        reason='safe and high time-saved/visual-error value'
        if not safety_ok:rejected_safety+=1;reason=safety_reason
        elif not cost_ok:rejected_cost+=1;reason='stroke/run renderer is cheaper'
        elif not value_ok:rejected_cost+=1;reason=f'fill saves too little for visual risk ({seconds_per_error:.2f}s/error)'
        decision=RegionDecision(idx,accepted_here,'OUTLINE_FILL' if accepted_here else 'CONNECTED_SCANLINES',confidence,risk,thin_score,
                                stroke_cost,fill_cost,saving if accepted_here else 0.0,visual_error,seconds_per_error,reason)
        decisions.append(decision)
        if accepted_here:
            region.update({'region_fill_id':idx,'render_method':'OUTLINE_FILL','fill_confidence':round(confidence,5),
                           'leak_risk':round(risk,5),'thin_neck_score':round(thin_score,5),
                           'stroke_cost_seconds':round(stroke_cost,5),'fill_cost_seconds':round(fill_cost,5),
                           'estimated_time_saved_seconds':round(saving,5),'visual_error_cost':round(visual_error,6),
                           'seconds_saved_per_visual_error':round(seconds_per_error,4),'outline_simplification':'exact-collinear'})
            accepted.append(region)
    area=max(1,int(image_size[0])*int(image_size[1]));accepted_pixels=sum(max(0,int(r.get('area_pixels',0) or 0)) for r in accepted)
    saved_strokes=sum(max(0,int(r.get('estimated_saved_strokes',0) or 0)) for r in accepted)
    total_time_saved=sum(float(r.get('estimated_time_saved_seconds',0) or 0) for r in accepted)
    total_regions=int(base_meta.get('total_components',len(regions or ())) or 0);fallback=max(0,total_regions-len(accepted))
    meta=dict(base_meta);meta.update({'enabled':True,'engine_name':'Region Fill Engine / Extra Fast 2.0','quality_preset':quality,
        'fill_aggressiveness':aggressiveness,'total_regions':total_regions,'fill_safe_regions':len(accepted),'fill_actions':len(accepted),
        'outline_paths':len(accepted),'fallback_stroke_regions':fallback,'rejected_by_cost':rejected_cost,'rejected_by_safety':rejected_safety,
        'fill_coverage_percent':round(accepted_pixels/area*100.0,3),'estimated_saved_strokes':saved_strokes,
        'estimated_time_saved_seconds':round(total_time_saved,3),'fill_value_policy':'seconds_saved_per_visual_error',
        'fill_value_threshold':value_threshold,'fill_absolute_saving_floor_seconds':absolute_saving_floor,
        'fill_color_batches':len({int(r.get('color_index',-1)) for r in accepted if int(r.get('color_index',-1))>=0}),
        'outline_simplification':'exact-collinear only','pixel_accurate_protected':False,
        'fallback_render_method':'CONNECTED_SCANLINES','decisions':[d.as_dict() for d in decisions[:80]],'decision_count':len(decisions)})
    return accepted,meta

def enrich_region_stats(meta: dict[str, Any] | None, *, source_strokes: int, final_paths: int) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    out = dict(meta)
    saved = max(0, int(out.get("estimated_saved_strokes", 0) or 0))
    source = max(0, int(source_strokes or 0))
    out["stroke_reduction_percent"] = round((saved / max(1, source + saved)) * 100.0, 3) if saved else 0.0
    out["source_strokes_after_fill"] = source
    out["final_execution_paths"] = max(0, int(final_paths or 0))
    return out


def estimate_fill_execution_seconds(regions: Iterable[dict[str, Any]], image_size: tuple[int, int], fitted: tuple[int, int], options: dict[str, Any]) -> dict[str, Any]:
    """Operation-level fill estimate using the same configured delays as execution."""
    rows = [dict(r) for r in (regions or ())]
    delivery = resolve_stroke_delivery(options, dry_run=False)
    fill_seconds = 0.0
    for region in rows:
        stored = region.get("fill_cost_seconds")
        if stored is not None:
            try:
                fill_seconds += max(0.0, float(stored))
                continue
            except Exception:
                pass
        _stroke, cost = _region_cost(region, options, image_size, fitted)
        fill_seconds += cost
    colors = {int(r.get("color_index", -1)) for r in rows if int(r.get("color_index", -1)) >= 0}
    tool_actions = len(options.get("fill_tool_actions") or ()) + len(options.get("fill_restore_actions") or ())
    # Preview planning intentionally does not resolve screen-coordinate tool
    # actions. If calibration says Fill is available, model the final Fill +
    # restore switch pair without inventing coordinates.
    if tool_actions == 0 and options.get("fill_tool_available"):
        tool_actions = 2
    tool_switch_seconds = len(colors) * tool_actions * max(.02, float(delivery.ui_control_delay))
    return {
        "fill_regions": len(rows),
        "fill_color_batches": len(colors),
        "fill_contour_and_click_seconds": round(fill_seconds, 4),
        "fill_tool_switch_seconds": round(tool_switch_seconds, 4),
        "total_seconds": round(fill_seconds + tool_switch_seconds, 4),
    }
