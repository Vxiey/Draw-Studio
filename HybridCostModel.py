"""Calibrated execution-cost model for Draw Studio hybrid planning.

The model translates geometry into *estimated wall-clock execution cost*.  It
uses the same profile-local DrawTimeCalibration data as the visible ETA when
available, and conservative StrokeDelivery/SpeedOptimizer defaults otherwise.
No native input, screen access or telemetry lives here.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from typing import Any, Iterable, Sequence

from StrokeDelivery import resolve_stroke_delivery
from SpeedOptimizer import normalize_speed, phase_delay

Point=tuple[int,int]
Path=Sequence[Point]


def _finite(value, default):
    try:
        value=float(value)
    except (TypeError,ValueError,OverflowError):
        return float(default)
    return value if math.isfinite(value) and value>=0 else float(default)


def _runtime_avg(runtime: dict[str,Any], *keys: str) -> float|None:
    for key in keys:
        item=runtime.get(key) if isinstance(runtime,dict) else None
        if not isinstance(item,dict): continue
        avg=_finite(item.get('average_seconds'),0.0)
        if avg<=0:
            try:
                count=max(0,int(item.get('count') or 0))
            except (TypeError, ValueError, OverflowError):
                continue
            total=_finite(item.get('total_seconds'),0.0)
            avg=total/count if count else 0.0
        if avg>0: return avg
    return None


def _path_length(path: Path, scale_x=1.0, scale_y=1.0) -> float:
    if not path or len(path)<2: return 0.0
    return sum(math.hypot((float(b[0])-float(a[0]))*scale_x,(float(b[1])-float(a[1]))*scale_y) for a,b in zip(path,path[1:]))


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

    @property
    def calibrated(self)->bool: return self.samples>0

    def travel_seconds(self,a:Point|None,b:Point)->float:
        if a is None:return 0.0
        return math.hypot((float(b[0])-a[0])*self.scale_x,
                          (float(b[1])-a[1])*self.scale_y)*self.travel_seconds_per_px

    def path_seconds(self,path:Path,*,cursor:Point|None=None)->float:
        if not path: return 0.0
        travel=self.travel_seconds(cursor,path[0])
        if len(path)==1:
            return travel+self.point_seconds
        seconds=(self.path_fixed_seconds+
                 _path_length(path,self.scale_x,self.scale_y)*self.draw_seconds_per_px)
        # Learned seconds/path is only a conservative floor; it is not treated
        # as a decomposition of drag/mouse costs.
        if self.learned_path_floor_seconds>0:
            seconds=max(seconds,self.learned_path_floor_seconds)
        return travel+seconds

    def paths_seconds(self,paths:Iterable[Path],*,cursor:Point|None=None)->float:
        total=0.0; cur=cursor
        for path in paths:
            if not path: continue
            total+=self.path_seconds(path,cursor=cur);cur=tuple(path[-1])
        return total

    def distance_path_seconds(self,distance_px:float,*,travel_px:float=0.0)->float:
        distance, travel = float(distance_px), float(travel_px)
        if not all(math.isfinite(v) and v >= 0 for v in (distance, travel)):
            raise ValueError('Path distances must be finite and non-negative.')
        draw = max(self.learned_path_floor_seconds, self.path_fixed_seconds + distance*self.draw_seconds_per_px)
        return travel*self.travel_seconds_per_px + draw

    def as_dict(self)->dict[str,Any]:
        out=asdict(self);out['calibrated']=self.calibrated
        for k,v in tuple(out.items()):
            if isinstance(v,float):out[k]=round(v,7)
        return out


def build_cost_model(options:dict[str,Any]|None)->HybridCostModel:
    options=dict(options or {})
    delivery=resolve_stroke_delivery(options,dry_run=False)
    speed=normalize_speed(options.get('speed','Balanced'))
    delay=_finite(options.get('delay'),0.0)
    step=max(1.0,_finite(getattr(delivery,'step_px',1.0),1.0))
    travel=_finite(phase_delay(delay,speed,'travel'),.004)
    path_delay=max(_finite(getattr(delivery,'min_path_delay',0.0),0.0),_finite(phase_delay(delay,speed,'path'),.004))
    boundary=_finite(phase_delay(delay,speed,'boundary'),.006)
    fixed=max(.001,_finite(getattr(delivery,'press_settle',0.0),0)+_finite(getattr(delivery,'release_settle',0.0),0)+boundary)
    ui=max(.02,_finite(getattr(delivery,'ui_control_delay',.08),.08))
    try:
        from DrawTimeCalibration import correction_for
        cal=correction_for(options)
    except Exception:
        cal={'samples':0,'operation_runtime':{},'seconds_per_completed_path':None}
    if not isinstance(cal, dict):
        cal={}
    try:
        samples=max(0,int(cal.get('samples') or 0))
    except (TypeError, ValueError, OverflowError):
        samples=0
    runtime=cal.get('operation_runtime') or {}
    measured_point=_runtime_avg(runtime,'dot','point')
    measured_path=_runtime_avg(runtime,'path','stroke','drag','mouse_drag')
    measured_travel=_runtime_avg(runtime,'travel','mouse_move')
    measured_color=_runtime_avg(runtime,'color_change','palette_change')
    measured_tool=_runtime_avg(runtime,'tool_change')
    measured_brush=_runtime_avg(runtime,'brush_change')
    measured_fill=_runtime_avg(runtime,'fill_action','bucket_fill')
    measured_verify=_runtime_avg(runtime,'verification','visual_verify')
    learned_floor=_finite(cal.get('seconds_per_completed_path'),0.0) if samples else 0.0
    # A typed path measurement describes a completed operation, not per-pixel
    # motion. Use it as the fixed/floor term and retain geometry-sensitive drag
    # cost from the delivery model.
    if measured_path is not None:
        fixed=max(fixed,measured_path*.72)
        learned_floor=max(learned_floor,measured_path*.82)
    source='calibrated-profile' if samples else 'conservative-default'
    return HybridCostModel(
        profile_key=str(options.get('profile_key') or options.get('profile_name') or 'generic'),
        source=source,samples=samples,
        travel_seconds_per_px=max(.00002,(measured_travel/80.0 if measured_travel else travel/max(16.0,step*8.0))),
        draw_seconds_per_px=max(.00004,path_delay/step),
        path_fixed_seconds=fixed,
        point_seconds=max(fixed*.72,path_delay,measured_point or 0.0),
        color_change_seconds=max(.0,measured_color if measured_color is not None else ui+.045),
        tool_change_seconds=max(.0,measured_tool if measured_tool is not None else ui+.06),
        brush_change_seconds=max(.0,measured_brush if measured_brush is not None else ui+.04),
        fill_action_seconds=max(.03,measured_fill if measured_fill is not None else ui+.12),
        verification_seconds=max(.0,measured_verify if measured_verify is not None else .035),
        learned_path_floor_seconds=max(.0,learned_floor),
        scale_x=max(.001,_finite(options.get("_hybrid_scale_x"),1.0)),
        scale_y=max(.001,_finite(options.get("_hybrid_scale_y"),1.0)),
    )
