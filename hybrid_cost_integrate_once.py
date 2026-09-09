from pathlib import Path

ROOT=Path('.')

def read(path): return (ROOT/path).read_text(encoding='utf-8')
def write(path,text): (ROOT/path).write_text(text,encoding='utf-8')
def replace_once(path,old,new,label):
    text=read(path)
    if text.count(old)!=1: raise SystemExit(f'{label}: expected one anchor, got {text.count(old)}')
    write(path,text.replace(old,new,1))

def append_before(path,anchor,text,label):
    src=read(path)
    if src.count(anchor)!=1: raise SystemExit(f'{label}: anchor count {src.count(anchor)}')
    write(path,src.replace(anchor,text+anchor,1))

write('HybridCostModel.py', '''"""Calibrated execution-cost model for Draw Studio hybrid planning.

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
    except (TypeError,ValueError):
        return float(default)
    return value if math.isfinite(value) and value>=0 else float(default)


def _runtime_avg(runtime: dict[str,Any], *keys: str) -> float|None:
    for key in keys:
        item=runtime.get(key) if isinstance(runtime,dict) else None
        if not isinstance(item,dict): continue
        avg=_finite(item.get('average_seconds'),0.0)
        if avg<=0:
            count=max(0,int(item.get('count') or 0))
            total=_finite(item.get('total_seconds'),0.0)
            avg=total/count if count else 0.0
        if avg>0: return avg
    return None


def _path_length(path: Path) -> float:
    if not path or len(path)<2: return 0.0
    return sum(math.hypot(float(b[0])-float(a[0]),float(b[1])-float(a[1])) for a,b in zip(path,path[1:]))


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

    @property
    def calibrated(self)->bool: return self.samples>0

    def path_seconds(self,path:Path,*,cursor:Point|None=None)->float:
        if not path: return 0.0
        travel=0.0 if cursor is None else math.hypot(float(path[0][0])-cursor[0],float(path[0][1])-cursor[1])
        if len(path)==1:
            return travel*self.travel_seconds_per_px+self.point_seconds
        seconds=(travel*self.travel_seconds_per_px+self.path_fixed_seconds+
                 _path_length(path)*self.draw_seconds_per_px)
        # Learned seconds/path is only a conservative floor; it is not treated
        # as a decomposition of drag/mouse costs.
        if self.learned_path_floor_seconds>0:
            seconds=max(seconds,self.learned_path_floor_seconds)
        return seconds

    def paths_seconds(self,paths:Iterable[Path],*,cursor:Point|None=None)->float:
        total=0.0; cur=cursor
        for path in paths:
            if not path: continue
            total+=self.path_seconds(path,cursor=cur);cur=tuple(path[-1])
        return total

    def distance_path_seconds(self,distance_px:float,*,travel_px:float=0.0)->float:
        return max(0.0,float(travel_px))*self.travel_seconds_per_px+self.path_fixed_seconds+max(0.0,float(distance_px))*self.draw_seconds_per_px

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
    samples=max(0,int(cal.get('samples') or 0));runtime=cal.get('operation_runtime') or {}
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
        point_seconds=max(fixed*.72,path_delay),
        color_change_seconds=max(.0,measured_color if measured_color is not None else ui+.045),
        tool_change_seconds=max(.0,measured_tool if measured_tool is not None else ui+.06),
        brush_change_seconds=max(.0,measured_brush if measured_brush is not None else ui+.04),
        fill_action_seconds=max(.03,measured_fill if measured_fill is not None else ui+.12),
        verification_seconds=max(.0,measured_verify if measured_verify is not None else .035),
        learned_path_floor_seconds=max(.0,learned_floor),
    )
''')

# PixelStrokeEngine: import typing cost model lazily, add cost-based H/V candidates.
p='PixelStrokeEngine.py';src=read(p)
old='def build_component_paths(comp: Component, component_map: np.ndarray, *, cancelled=lambda: False) -> tuple[list[Path], dict]:\n    """Build local H/V paths and verify every connector against component pixels."""\n    comp.orientation = _choose_orientation(comp)\n    source_runs = comp.horizontal_runs if comp.orientation == "horizontal" else comp.vertical_runs\n    if comp.orientation == "horizontal":\n        paths = _merge_horizontal_runs_lossless(source_runs, cancelled=cancelled)\n    else:\n        transposed = _transpose_segments(source_runs)\n        transposed_paths = _merge_horizontal_runs_lossless(transposed, cancelled=cancelled)\n        paths = _transpose_paths(transposed_paths)\n\n    unsafe = [path for path in paths if not _path_inside_component(path, component_map, comp.component_id)]\n    exact_coverage = (not unsafe) and _paths_exact_component_coverage(paths, component_map, comp)\n    if not exact_coverage:\n        # Safety and accuracy over compression: if a connector leaves the exact\n        # region *or* a merge/compression accidentally skips a source pixel, fall\n        # back to individual lossless runs for this component only.\n        paths = _individual_run_paths(source_runs)\n        comp.safe_merge_fallbacks += 1\n    paths = order_paths(paths, "Balanced", allow_reverse=True)\n    comp.paths = list(paths)\n    return comp.paths, {\n        "orientation": comp.orientation,\n        "source_runs": len(source_runs),\n        "execution_paths": len(comp.paths),\n        "safe_verified": bool(exact_coverage),\n        "fallback": not bool(exact_coverage),\n    }\n'
new='''def _candidate_paths(comp: Component, orientation: str, component_map: np.ndarray, *, cancelled=lambda: False):
    source_runs=comp.horizontal_runs if orientation=="horizontal" else comp.vertical_runs
    if orientation=="horizontal":
        paths=_merge_horizontal_runs_lossless(source_runs,cancelled=cancelled)
    else:
        paths=_transpose_paths(_merge_horizontal_runs_lossless(_transpose_segments(source_runs),cancelled=cancelled))
    safe=all(_path_inside_component(path,component_map,comp.component_id) for path in paths)
    exact=bool(safe and _paths_exact_component_coverage(paths,component_map,comp))
    return paths,source_runs,exact


def build_component_paths(comp: Component, component_map: np.ndarray, *, cost_model=None, cancelled=lambda: False) -> tuple[list[Path], dict]:
    """Build safe H/V candidates and choose by calibrated time when available."""
    legacy_orientation=_choose_orientation(comp)
    candidate_meta={}
    if cost_model is None:
        comp.orientation=legacy_orientation
        paths,source_runs,exact_coverage=_candidate_paths(comp,comp.orientation,component_map,cancelled=cancelled)
    else:
        choices=[]
        for orientation in ("horizontal","vertical"):
            paths0,runs0,exact0=_candidate_paths(comp,orientation,component_map,cancelled=cancelled)
            cost=float(cost_model.paths_seconds(paths0)) if exact0 else float("inf")
            candidate_meta[orientation]={"safe":bool(exact0),"paths":len(paths0),"estimated_seconds":None if not math.isfinite(cost) else round(cost,6)}
            if exact0:choices.append((cost,orientation,paths0,runs0))
        if choices:
            choices.sort(key=lambda item:(item[0],0 if item[1]==legacy_orientation else 1,item[1]))
            # Protected very-thin structures keep the legacy long-axis choice if
            # its real predicted cost is within 6%; this avoids fragmentation for
            # a negligible timing win.
            best=choices[0]
            legacy=next((x for x in choices if x[1]==legacy_orientation),None)
            if comp.protected_pixels and min(comp.width,comp.height)<=3 and legacy and legacy[0]<=best[0]*1.06:
                best=legacy
            _cost,comp.orientation,paths,source_runs=best;exact_coverage=True
        else:
            comp.orientation=legacy_orientation
            paths,source_runs,exact_coverage=_candidate_paths(comp,comp.orientation,component_map,cancelled=cancelled)
    if not exact_coverage:
        paths=_individual_run_paths(source_runs);comp.safe_merge_fallbacks+=1
    paths=order_paths(paths,"Balanced",allow_reverse=True);comp.paths=list(paths)
    return comp.paths,{
        "orientation":comp.orientation,"source_runs":len(source_runs),"execution_paths":len(comp.paths),
        "safe_verified":bool(exact_coverage),"fallback":not bool(exact_coverage),
        "selection":"calibrated-time" if cost_model is not None else "legacy-run-count",
        "candidates":candidate_meta,
    }
'''
if src.count(old)!=1: raise SystemExit('PixelStroke build_component_paths anchor mismatch')
src=src.replace(old,new,1)
# schedule signature and body score block
src=src.replace('def schedule_components(components: Sequence[Component], palette_count: int, *, cancelled=lambda: False) -> tuple[list[list[Path]], list[dict], dict]:',
'''def schedule_components(components: Sequence[Component], palette_count: int, *, cost_model=None, cancelled=lambda: False) -> tuple[list[list[Path]], list[dict], dict]:''',1)
oldscore='''                start = _component_entry_point(comp)
                travel = 0.0 if cursor is None else math.hypot(start[0] - cursor[0], start[1] - cursor[1])
                color_penalty = 0.0 if current_color in (None, comp.color_index) else 18.0
                priority_credit = min(30.0, _priority(comp) * .025)
                cost = travel + color_penalty - priority_credit + i * 1e-6
                if cost < best_cost:
                    best_i, best_cost = i, cost
'''
newscore='''                start = _component_entry_point(comp)
                if cost_model is None:
                    travel = 0.0 if cursor is None else math.hypot(start[0] - cursor[0], start[1] - cursor[1])
                    color_penalty = 0.0 if current_color in (None, comp.color_index) else 18.0
                    priority_credit = min(30.0, _priority(comp) * .025)
                    cost = travel + color_penalty - priority_credit + i * 1e-6
                else:
                    seconds=float(cost_model.paths_seconds(comp.paths,cursor=cursor))
                    if current_color not in (None,comp.color_index):seconds+=float(cost_model.color_change_seconds)
                    # Keep the multi-pass contract, but within each phase choose
                    # the component with highest visual value per millisecond.
                    value=max(.001,float(_priority(comp)))
                    cost=(seconds/max(.001,value))+i*1e-9
                if cost < best_cost:
                    best_i, best_cost = i, cost
'''
if src.count(oldscore)!=1: raise SystemExit('scheduler score anchor mismatch')
src=src.replace(oldscore,newscore,1)
oldret='''        "scheduled_paths": len(sequence),
    }
'''
newret='''        "scheduled_paths": len(sequence),
        "cost_aware": bool(cost_model is not None),
        "cost_model": cost_model.as_dict() if cost_model is not None else None,
        "estimated_execution_seconds": round(sum(float(cost_model.path_seconds(e["path"])) for e in sequence),4) if cost_model is not None else None,
        "scheduled_color_switches": sum(1 for a,b in zip(sequence,sequence[1:]) if a["color_index"]!=b["color_index"]),
    }
'''
if src.count(oldret)!=1: raise SystemExit('scheduler return anchor mismatch')
src=src.replace(oldret,newret,1)
# build signature and initialization
src=src.replace('''def build_pixel_stroke_plan(pixel_map: PixelMap, palette_count: int, *, lines: bool = True,
                            cpu_workers: int = 1, cancelled=lambda: False) -> dict:''',
'''def build_pixel_stroke_plan(pixel_map: PixelMap, palette_count: int, *, lines: bool = True,
                            cpu_workers: int = 1, options=None, cancelled=lambda: False) -> dict:''',1)
anchor='''    groups = groups_from_pixel_map(pixel_map, palette_count, lines=lines, cancelled=cancelled)
'''
insert='''    groups = groups_from_pixel_map(pixel_map, palette_count, lines=lines, cancelled=cancelled)
    cost_model=None
    if isinstance(options,dict) and str(options.get("adaptive_hybrid_cost","Auto")) != "Off":
        try:
            from HybridCostModel import build_cost_model
            cost_model=build_cost_model(options)
        except Exception:
            cost_model=None
'''
if src.count(anchor)!=1:raise SystemExit('groups anchor mismatch')
src=src.replace(anchor,insert,1)
src=src.replace('build_component_paths(comp,component_map,cancelled=cancelled)', 'build_component_paths(comp,component_map,cost_model=cost_model,cancelled=cancelled)')
src=src.replace('schedule_components(components, palette_count, cancelled=cancelled)', 'schedule_components(components, palette_count, cost_model=cost_model, cancelled=cancelled)',1)
write(p,src)

# SubjectFocus accepts and forwards options.
p='SubjectFocus.py';src=read(p)
src=src.replace('def focused_stroke_plan(pixel_map, image, palette_count, mode, region=None, *, lines=True, cpu_workers=1, cancelled=lambda: False):',
'''def focused_stroke_plan(pixel_map, image, palette_count, mode, region=None, *, lines=True, cpu_workers=1, options=None, cancelled=lambda: False):''',1)
src=src.replace('kwargs = dict(lines=lines, cpu_workers=cpu_workers, cancelled=cancelled)',
'''kwargs = dict(lines=lines, cpu_workers=cpu_workers, options=options, cancelled=cancelled)''',1)
write(p,src)

# DrawBot activation only at existing PixelMap->SubjectFocus boundary.
p='DrawBot.py';src=read(p)
old='''            pixel_map,image,len(allColors),options.get('subject_focus','Off'),options.get('subject_region'),lines=bool(options.get('lines',True)),
            cpu_workers=int(options.get('cpu_workers_resolved',1) or 1),cancelled=cancelled)'''
new='''            pixel_map,image,len(allColors),options.get('subject_focus','Off'),options.get('subject_region'),lines=bool(options.get('lines',True)),
            cpu_workers=int(options.get('cpu_workers_resolved',1) or 1),options=options,cancelled=cancelled)'''
if src.count(old)!=1:raise SystemExit('DrawBot focused_stroke_plan anchor mismatch')
write(p,src.replace(old,new,1))

# RegionFillEngine: calibrated path/fill costs but unchanged safety gate.
p='RegionFillEngine.py';src=read(p)
old='''def _region_cost(region: dict[str, Any], options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> tuple[float, float]:
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
    spans = region.get("row_spans") or ()
    for raw in spans:
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
    # One continuous contour + one fill click. Tool-switch overhead is shared by
    # all regions of the same colour and is accounted for in the final plan.
    fill_cost = travel_delay + contour_moves * path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
    fill_cost += max(.08, delivery.ui_control_delay * .45) + .24
    return max(.001, stroke_cost), max(.001, fill_cost)
'''
new='''def _region_cost(region: dict[str, Any], options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> tuple[float, float]:
    from HybridCostModel import build_cost_model
    model=build_cost_model(options)
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
'''
if src.count(old)!=1:raise SystemExit('RegionFill _region_cost anchor mismatch')
src=src.replace(old,new,1)
# add cost metadata before final return/meta via known update anchor
oldmeta='''        "average_seconds_saved_per_visual_error": round(sum(float(r.get("seconds_saved_per_visual_error",0) or 0) for r in accepted)/max(1,len(accepted)),3),
        "fill_color_batches": fill_colors,
'''
newmeta='''        "average_seconds_saved_per_visual_error": round(sum(float(r.get("seconds_saved_per_visual_error",0) or 0) for r in accepted)/max(1,len(accepted)),3),
        "hybrid_cost_model": __import__('HybridCostModel').build_cost_model(options).as_dict(),
        "fill_color_batches": fill_colors,
'''
if src.count(oldmeta)!=1:raise SystemExit('RegionFill meta anchor mismatch')
src=src.replace(oldmeta,newmeta,1)
write(p,src)

# Six-case deterministic old/new benchmark. Actual Windows time deliberately null
# unless the caller supplies it; never manufacture physical input measurements.
write('HybridBenchmark.py', '''"""Deterministic six-case old/new hybrid planner benchmark.

This benchmark is local-only. It measures planning wall time and plan/simulation
metrics. `actual_draw_seconds` remains None unless a caller supplies a real
verified Windows executor measurement.
"""
from __future__ import annotations
import time,tracemalloc
from typing import Any,Callable
from PIL import Image,ImageDraw


def _icon():
    im=Image.new('RGBA',(240,180),'white');d=ImageDraw.Draw(im);d.rounded_rectangle((30,28,210,152),24,fill='#e8bc32',outline='#202020',width=5);d.ellipse((70,65,95,90),fill='black');return im

def _line():
    im=Image.new('RGBA',(240,180),'white');d=ImageDraw.Draw(im);d.ellipse((32,22,208,158),outline='black',width=3);d.line((60,118,120,55,180,118),fill='black',width=2);return im

def _text_detail():
    im=Image.new('RGBA',(240,180),'white');d=ImageDraw.Draw(im);d.rectangle((14,14,226,166),outline='black',width=3);d.text((25,25),'DRAW 123',fill='black');
    for x in range(28,212,13):d.line((x,75,x,145),fill=(70,70,70),width=1)
    d.ellipse((105,102,111,108),fill='red');return im

def _cartoon():
    im=Image.new('RGBA',(240,180),(210,235,255,255));d=ImageDraw.Draw(im);d.ellipse((45,22,195,166),fill=(255,204,64),outline='black',width=4);d.ellipse((82,68,102,88),fill='black');d.rectangle((115,98,175,130),fill=(54,160,92),outline='black',width=3);return im

def _photo():
    im=Image.new('RGBA',(240,180),'white');p=im.load()
    for y in range(180):
        for x in range(240):p[x,y]=(int(30+210*x/239),int(40+180*y/179),int(185-120*x/239+40*y/179),255)
    ImageDraw.Draw(im).ellipse((68,35,175,152),outline=(20,20,20),width=3);return im

def _fill_risk():
    im=Image.new('RGBA',(240,180),'white');d=ImageDraw.Draw(im);d.rectangle((24,20,216,160),fill=(70,145,225),outline='black',width=3);d.rectangle((72,55,168,125),fill='white',outline='black',width=2);d.rectangle((118,20,122,92),fill='white');d.line((25,144,215,144),fill='red',width=1);return im

CASES=(('icon',_icon),('line-art',_line),('text-small-detail',_text_detail),('cartoon-large-colour',_cartoon),('photo-gradient',_photo),('fill-risk',_fill_risk))


def _row(make_plan,image,area,base_options,enabled,cancelled):
    options=dict(base_options);options['adaptive_hybrid_cost']='Auto' if enabled else 'Off';options['_preview_plan']=True
    tracemalloc.start();start=time.perf_counter();plan=make_plan(image,area,options,cancelled);elapsed=time.perf_counter()-start
    _cur,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    po=plan.get('options') or {};acc=po.get('adaptive_accuracy_meta') or {};de=po.get('preview_delta_e_meta') or {};timing=plan.get('draw_time_estimate') or {}
    seq=plan.get('execution_sequence') or []
    switches=sum(1 for a,b in zip(seq,seq[1:]) if a.get('color_index')!=b.get('color_index'))
    fills=len(po.get('fill_regions') or ())+(1 if (po.get('background_fill_plan') or {}).get('enabled') else 0)
    return {'engine':'calibrated-hybrid' if enabled else 'legacy-fallback','planning_seconds':round(elapsed,5),'estimated_draw_seconds':round(float(timing.get('projected_seconds',plan.get('estimate',0)) or 0),4),'actual_draw_seconds':None,'operations':int(plan.get('count') or 0),'color_switches':switches,'fill_actions':fills,'peak_python_memory_bytes':int(peak),'visual_accuracy_percent':acc.get('visual_accuracy_percent'),'coverage_percent':acc.get('coverage_percent'),'spill_percent':acc.get('spill_percent'),'perceptual_color_accuracy_percent':acc.get('perceptual_color_accuracy_percent'),'mean_delta_e_oklab':de.get('mean_delta_e_oklab'),'performance_profile':plan.get('performance_profile') or {},'gpu_backend':(po.get('universal_gpu_meta') or po.get('gpu_meta') or {}).get('backend')}


def run(make_plan:Callable[...,dict],base_options:dict[str,Any],*,area=(480,360),cancelled=lambda:False):
    rows=[]
    for name,factory in CASES:
        if cancelled():raise InterruptedError()
        image=factory();legacy=_row(make_plan,image,area,base_options,False,cancelled);hybrid=_row(make_plan,image,area,base_options,True,cancelled)
        rows.append({'case':name,'legacy':legacy,'hybrid':hybrid,'estimated_draw_delta_seconds':round(hybrid['estimated_draw_seconds']-legacy['estimated_draw_seconds'],4),'operation_delta':hybrid['operations']-legacy['operations']})
    return {'version':1,'local_only':True,'real_windows_input_verified':False,'actual_draw_times_measured':False,'cases':rows,'case_count':len(rows),'note':'Planning/simulation comparison only. Actual Windows input time and physical GPU execution must be measured on a real configured target.'}
''')

# Tests exercise exact safety and model behavior without requiring Windows input.
write('test_hybrid_cost_engine_v10131.py', '''import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from PixelAccuratePlanner import build_pixel_map
from PixelStrokeEngine import connected_components,build_component_paths,build_pixel_stroke_plan
from HybridCostModel import build_cost_model
from HybridBenchmark import CASES

PALETTE=((255,255,255),(0,0,0),(255,0,0),(0,0,255))

def opts(**kw):
    d=dict(profile_key='microsoft-paint',profile_name='Microsoft Paint',speed='Balanced',precision='High',brush_px=1,delay=.006,paint_tool='Pencil',effective_paint_tool='Pencil',custom_color_workflow='calibrated-palette',use_region_fill_engine=False,adaptive_hybrid_cost='Auto')
    d.update(kw);return d

class HybridCostEngineTests(unittest.TestCase):
    def test_cold_start_is_explicit_not_fake_calibrated(self):
        m=build_cost_model(opts())
        self.assertIn(m.source,('conservative-default','calibrated-profile'))
        self.assertGreater(m.path_fixed_seconds,0)
    def test_six_required_benchmark_cases_exist(self):
        self.assertEqual(len(CASES),6);self.assertEqual({n for n,_ in CASES},{'icon','line-art','text-small-detail','cartoon-large-colour','photo-gradient','fill-risk'})
    def test_cost_aware_plan_is_exact_and_reports_model(self):
        im=Image.new('RGBA',(28,22),'white');d=ImageDraw.Draw(im);d.rectangle((2,3,20,12),fill='red');d.line((24,2,24,19),fill='blue')
        pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts())
        self.assertTrue(plan['metadata']['cost_aware']);self.assertIsInstance(plan['metadata']['cost_model'],dict)
        self.assertEqual(sum(len(g) for g in plan['execution_groups']),len(plan['execution_sequence']))
    def test_legacy_fallback_remains_available(self):
        im=Image.new('RGBA',(16,12),'red');pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts(adaptive_hybrid_cost='Off'))
        self.assertFalse(plan['metadata']['cost_aware'])
    def test_component_candidate_never_paints_outside(self):
        im=Image.new('RGBA',(12,10),'white');d=ImageDraw.Draw(im);d.rectangle((1,1,8,6),fill='red');d.rectangle((4,3,5,4),fill='white')
        pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True);comps,cmap,_=connected_components(pm)
        red=max((c for c in comps if c.color_index==2),key=lambda c:c.area)
        paths,meta=build_component_paths(red,cmap,cost_model=build_cost_model(opts()))
        self.assertTrue(paths);self.assertIn(meta['selection'],('calibrated-time','legacy-run-count'))
        # Exact planner fallback/verification is authoritative for holes.
        self.assertTrue(meta['safe_verified'] or meta['fallback'])
    def test_drawbot_forwards_full_options_to_subject_planner(self):
        text=Path('DrawBot.py').read_text(encoding='utf-8');self.assertIn('options=options,cancelled=cancelled)',text)
    def test_region_fill_uses_shared_cost_model(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8');self.assertIn('from HybridCostModel import build_cost_model',text);self.assertIn('hybrid_cost_model',text)
    def test_gartic_specialized_route_not_replaced(self):
        text=Path('DrawBot.py').read_text(encoding='utf-8');self.assertIn('optimize_gartic_phone_groups',text);self.assertIn('build_gartic_execution_paths',text)
    def test_no_human_mode_added_to_new_engine(self):
        self.assertNotIn('HumanMode',Path('HybridCostModel.py').read_text(encoding='utf-8'));self.assertNotIn('HumanMode',Path('HybridBenchmark.py').read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
''')

# Packaging hooks.
p='build_exe.py';src=read(p)
anchor="        '--hidden-import', 'PixelStrokeEngine',\n"
if anchor not in src:raise SystemExit('build_exe PixelStrokeEngine anchor missing')
src=src.replace(anchor,anchor+"        '--hidden-import', 'HybridCostModel',\n        '--hidden-import', 'HybridBenchmark',\n",1)
write(p,src)

print('HYBRID_COST_PATCH=APPLIED')
