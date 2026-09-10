"""Calibrated execution-cost model for Image Draw Bot hybrid planning.

Cost Model v2 keeps the conservative cold-start geometry model, but treats
profile-local timing as evidence rather than an all-or-nothing switch. Measured
operation timings and the learned actual/predicted ratio are blended according
to sample count and historical MAPE. This prevents one noisy draw from replacing
stable defaults while allowing repeated accurate calibration to dominate.

The model remains pure: no native input, screen access, files or network live
here. DrawTimeCalibration owns persistence and is loaded through a narrow helper.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from typing import Any, Iterable, Sequence

from StrokeDelivery import resolve_stroke_delivery
from SpeedOptimizer import normalize_speed, phase_delay

Point=tuple[int,int]
Path=Sequence[Point]
MODEL_VERSION=2


def _finite(value, default):
    try:
        value=float(value)
    except (TypeError,ValueError,OverflowError):
        return float(default)
    return value if math.isfinite(value) and value>=0 else float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _runtime_avg(runtime: dict[str,Any], *keys: str) -> float|None:
    for key in keys:
        item=runtime.get(key) if isinstance(runtime,dict) else None
        if not isinstance(item,dict):
            continue
        avg=_finite(item.get('average_seconds'),0.0)
        if avg<=0:
            try:
                count=max(0,int(item.get('count') or 0))
            except (TypeError,ValueError,OverflowError):
                continue
            total=_finite(item.get('total_seconds'),0.0)
            avg=total/count if count else 0.0
        if avg>0:
            return avg
    return None


def _path_length(path: Path, scale_x=1.0, scale_y=1.0) -> float:
    if not path or len(path)<2:
        return 0.0
    return sum(math.hypot((float(b[0])-float(a[0]))*scale_x,
                          (float(b[1])-float(a[1]))*scale_y)
               for a,b in zip(path,path[1:]))


def _calibration_confidence(samples: int, mape: float|None) -> float:
    """Return bounded evidence confidence from history depth and prediction error."""
    samples=max(0,int(samples or 0))
    if samples<=0:
        return 0.0
    sample_evidence=1.0-math.exp(-samples/5.0)
    if mape is None:
        error_quality=.75
    else:
        error_quality=max(.15,1.0-min(1.5,max(0.0,float(mape)))/1.5)
    return _clamp(sample_evidence*error_quality,0.0,1.0)


def _blend(default: float, measured: float|None, confidence: float) -> float:
    if measured is None:
        return float(default)
    weight=_clamp(confidence,0.0,1.0)
    return float(default)*(1.0-weight)+float(measured)*weight


def _load_calibration(options: dict[str,Any]) -> dict[str,Any]:
    override=options.get('_hybrid_cost_calibration_override')
    if isinstance(override,dict):
        return dict(override)
    try:
        from DrawTimeCalibration import correction_for
        result=correction_for(options)
    except Exception:
        result={}
    return dict(result) if isinstance(result,dict) else {}


def _count(value: Any) -> int:
    try:
        return max(0,int(value or 0))
    except (TypeError,ValueError,OverflowError):
        return 0


@dataclass(frozen=True)
class HybridCostModel:
    profile_key: str
    source: str
    samples: int
    travel_seconds_per_px: float
    draw_seconds_per_px: float
    path_fixed_seconds: float
    point_seconds: float
    color_change_seconds: float
    tool_change_seconds: float
    brush_change_seconds: float
    fill_action_seconds: float
    verification_seconds: float
    learned_path_floor_seconds: float
    scale_x: float = 1.0
    scale_y: float = 1.0
    model_version: int = MODEL_VERSION
    calibration_confidence: float = 0.0
    calibration_mape: float|None = None
    correction_ratio: float = 1.0
    effective_correction_ratio: float = 1.0
    uncertainty_multiplier: float = 1.0
    travel_reference_px: float = 80.0

    @property
    def calibrated(self)->bool:
        return self.samples>0

    @property
    def high_confidence(self)->bool:
        return self.calibration_confidence>=.65

    def travel_seconds(self,a:Point|None,b:Point)->float:
        if a is None:
            return 0.0
        return math.hypot((float(b[0])-float(a[0]))*self.scale_x,
                          (float(b[1])-float(a[1]))*self.scale_y)*self.travel_seconds_per_px

    def path_seconds(self,path:Path,*,cursor:Point|None=None)->float:
        if not path:
            return 0.0
        travel=self.travel_seconds(cursor,path[0])
        if len(path)==1:
            return travel+self.point_seconds
        seconds=(self.path_fixed_seconds+
                 _path_length(path,self.scale_x,self.scale_y)*self.draw_seconds_per_px)
        if self.learned_path_floor_seconds>0:
            seconds=max(seconds,self.learned_path_floor_seconds)
        return travel+seconds

    def paths_seconds(self,paths:Iterable[Path],*,cursor:Point|None=None)->float:
        total=0.0
        cur=cursor
        for path in paths:
            if not path:
                continue
            total+=self.path_seconds(path,cursor=cur)
            cur=tuple(path[-1])
        return total

    def distance_path_seconds(self,distance_px:float,*,travel_px:float=0.0)->float:
        distance,travel=float(distance_px),float(travel_px)
        if not all(math.isfinite(v) and v>=0 for v in (distance,travel)):
            raise ValueError('Path distances must be finite and non-negative.')
        draw=max(self.learned_path_floor_seconds,
                 self.path_fixed_seconds+distance*self.draw_seconds_per_px)
        return travel*self.travel_seconds_per_px+draw

    def operation_seconds(self,paths:Iterable[Path]=(),*,cursor:Point|None=None,
                          color_changes:int=0,tool_changes:int=0,brush_changes:int=0,
                          fill_actions:int=0,verification_actions:int=0)->float:
        """Return one shared expected wall-clock cost for geometry + UI operations."""
        return (
            self.paths_seconds(paths,cursor=cursor)
            +_count(color_changes)*self.color_change_seconds
            +_count(tool_changes)*self.tool_change_seconds
            +_count(brush_changes)*self.brush_change_seconds
            +_count(fill_actions)*self.fill_action_seconds
            +_count(verification_actions)*self.verification_seconds
        )

    def execution_breakdown(self,paths:Iterable[Path]=(),*,cursor:Point|None=None,
                            color_changes:int=0,tool_changes:int=0,brush_changes:int=0,
                            fill_actions:int=0,verification_actions:int=0)->dict[str,float|int]:
        path_seconds=self.paths_seconds(paths,cursor=cursor)
        color_seconds=_count(color_changes)*self.color_change_seconds
        tool_seconds=_count(tool_changes)*self.tool_change_seconds
        brush_seconds=_count(brush_changes)*self.brush_change_seconds
        fill_seconds=_count(fill_actions)*self.fill_action_seconds
        verification_seconds=_count(verification_actions)*self.verification_seconds
        total=path_seconds+color_seconds+tool_seconds+brush_seconds+fill_seconds+verification_seconds
        return {
            'model_version':self.model_version,
            'path_seconds':path_seconds,
            'color_seconds':color_seconds,
            'tool_seconds':tool_seconds,
            'brush_seconds':brush_seconds,
            'fill_seconds':fill_seconds,
            'verification_seconds':verification_seconds,
            'total_seconds':total,
            'risk_adjusted_seconds':self.risk_adjusted_seconds(total),
        }

    def risk_adjusted_seconds(self,seconds:float)->float:
        value=float(seconds)
        if not math.isfinite(value) or value<0:
            raise ValueError('Seconds must be finite and non-negative.')
        return value*self.uncertainty_multiplier

    def as_dict(self)->dict[str,Any]:
        out=asdict(self)
        out['calibrated']=self.calibrated
        out['high_confidence']=self.high_confidence
        for key,value in tuple(out.items()):
            if isinstance(value,float):
                out[key]=round(value,7)
        return out


def build_cost_model(options:dict[str,Any]|None)->HybridCostModel:
    options=dict(options or {})
    delivery=resolve_stroke_delivery(options,dry_run=False)
    speed=normalize_speed(options.get('speed','Balanced'))
    delay=_finite(options.get('delay'),0.0)
    step=max(1.0,_finite(getattr(delivery,'step_px',1.0),1.0))
    travel_phase=_finite(phase_delay(delay,speed,'travel'),.004)
    path_delay=max(_finite(getattr(delivery,'min_path_delay',0.0),0.0),
                   _finite(phase_delay(delay,speed,'path'),.004))
    boundary=_finite(phase_delay(delay,speed,'boundary'),.006)
    default_fixed=max(.001,_finite(getattr(delivery,'press_settle',0.0),0)
                      +_finite(getattr(delivery,'release_settle',0.0),0)+boundary)
    ui=max(.02,_finite(getattr(delivery,'ui_control_delay',.08),.08))

    cal=_load_calibration(options)
    samples=_count(cal.get('samples'))
    raw_mape=cal.get('mape')
    try:
        mape=float(raw_mape) if raw_mape is not None else None
        if mape is not None and (not math.isfinite(mape) or mape<0):
            mape=None
    except (TypeError,ValueError,OverflowError):
        mape=None
    confidence=_calibration_confidence(samples,mape)
    ratio=_clamp(_finite(cal.get('ratio'),1.0),.55,4.0) if samples else 1.0
    effective_ratio=_clamp(1.0+confidence*(ratio-1.0),.70,2.50)

    runtime=cal.get('operation_runtime') or {}
    measured_point=_runtime_avg(runtime,'dot','point')
    measured_path=_runtime_avg(runtime,'path','stroke','drag','mouse_drag')
    measured_travel=_runtime_avg(runtime,'travel','mouse_move')
    measured_color=_runtime_avg(runtime,'color_change','palette_change')
    measured_tool=_runtime_avg(runtime,'tool_change')
    measured_brush=_runtime_avg(runtime,'brush_change')
    measured_fill=_runtime_avg(runtime,'fill_action','bucket_fill')
    measured_verify=_runtime_avg(runtime,'verification','visual_verify')

    try:
        travel_reference=max(8.0,min(4096.0,float(options.get('_hybrid_travel_reference_px',80.0) or 80.0)))
    except (TypeError,ValueError,OverflowError):
        travel_reference=80.0
    default_travel=max(.00002,travel_phase/max(16.0,step*8.0))
    default_draw=max(.00004,path_delay/step)

    corrected_travel=default_travel*effective_ratio
    measured_travel_per_px=(measured_travel/travel_reference) if measured_travel is not None else None
    travel_per_px=max(.00002,_blend(corrected_travel,measured_travel_per_px,confidence))
    draw_per_px=max(.00004,default_draw*effective_ratio)

    fixed_base=default_fixed*effective_ratio
    fixed_target=max(default_fixed,measured_path*.72) if measured_path is not None else None
    fixed=max(.001,_blend(fixed_base,fixed_target,confidence))

    floor=0.0
    if measured_path is not None:
        floor=max(0.0,measured_path*.82*confidence)
    elif samples:
        learned=_finite(cal.get('seconds_per_completed_path'),0.0)
        floor=max(0.0,learned*.82*confidence)

    point_default=max(fixed*.72,path_delay*effective_ratio)
    # A typed dot/point runtime is the complete atomic operation, not an inferred
    # coefficient. Preserve it as a hard lower bound so confidence blending can
    # never predict a known point operation faster than its measured runtime.
    point=max(.001,point_default,measured_point or 0.0)

    def operation(default: float, measured: float|None, *, minimum: float=0.0) -> float:
        expected=max(minimum,float(default)*effective_ratio)
        return max(minimum,_blend(expected,measured,confidence))

    color=operation(ui+.045,measured_color)
    tool=operation(ui+.06,measured_tool)
    brush=operation(ui+.04,measured_brush)
    fill=operation(max(.03,ui+.12),measured_fill,minimum=.03)
    verification=operation(.035,measured_verify)

    if samples<=0:
        uncertainty=1.0
    else:
        observed_error=min(1.0,mape if mape is not None else .35)
        uncertainty=1.0+(1.0-confidence)*.10+observed_error*(.30-.12*confidence)
        uncertainty=_clamp(uncertainty,1.0,1.60)

    source='calibrated-profile-v2' if samples else 'conservative-default'
    return HybridCostModel(
        profile_key=str(options.get('profile_key') or options.get('profile_name') or 'generic'),
        source=source,
        samples=samples,
        travel_seconds_per_px=travel_per_px,
        draw_seconds_per_px=draw_per_px,
        path_fixed_seconds=fixed,
        point_seconds=point,
        color_change_seconds=color,
        tool_change_seconds=tool,
        brush_change_seconds=brush,
        fill_action_seconds=fill,
        verification_seconds=verification,
        learned_path_floor_seconds=floor,
        scale_x=max(.001,_finite(options.get('_hybrid_scale_x'),1.0)),
        scale_y=max(.001,_finite(options.get('_hybrid_scale_y'),1.0)),
        model_version=MODEL_VERSION,
        calibration_confidence=confidence,
        calibration_mape=mape,
        correction_ratio=ratio,
        effective_correction_ratio=effective_ratio,
        uncertainty_multiplier=uncertainty,
        travel_reference_px=travel_reference,
    )
