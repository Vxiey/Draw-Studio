"""Adaptive Region Hybrid 4.0 for Draw Studio v1.0.132-beta.

This is a planning/orchestration layer, not a second native-input engine. It
reuses Draw Studio's proven color pipeline, exact component topology, Fill
detector, profile calibration, preview and single guarded mouse executor.

For each exact colour component it evaluates safe horizontal/vertical connected
run plans (and verified multi-brush interior plans when the target exposes real
brush-size controls), using calibrated *time* rather than stroke count. Native
Fill remains optional and is accepted only after RegionFillEngine plus the
stateful contour/flood simulator agree. Under a deadline, components are
scheduled by simulated visual gain per millisecond with coarse spatial seeding
so a recognisable whole appears before optional detail.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import time
from typing import Any, Callable, Sequence

import numpy as np
from PIL import Image, ImageDraw

from AdaptiveBrushEngine import verified_brush_sizes
from ExecutionCostModel import build_cost_model
from PixelAccuratePlanner import PixelMap
from PixelStrokeEngine import connected_components
from StatefulFillSimulation import filter_stateful_fill_regions

ADAPTIVE_HYBRID_RENDER_STYLE = "Adaptive Hybrid 4.0"
ADAPTIVE_HYBRID_VERSION = "4.0"
PHASES = ("foundation", "structure", "detail", "correction")


@dataclass
class RegionChoice:
    component_id: int
    color_index: int
    method: str
    phase: str
    area: int
    importance: float
    edge: float
    protected_pixels: int
    estimated_seconds: float
    visual_gain: float
    gain_per_ms: float
    paths: int
    brush_px: int
    exact: bool
    reason: str

    def as_dict(self):
        out=asdict(self)
        for key,value in tuple(out.items()):
            if isinstance(value,float):out[key]=round(value,6)
        return out


def is_adaptive_hybrid(options: dict[str, Any]) -> bool:
    return (str(options.get("render_style") or "") == ADAPTIVE_HYBRID_RENDER_STYLE
            and not bool(options.get("_adaptive_hybrid_inner")))


def _cancel(cancelled):
    if cancelled():raise InterruptedError()


def _raster_line(index: np.ndarray, color: int, stroke) -> None:
    h,w=index.shape
    try:x0,y0,x1,y1=map(int,stroke)
    except Exception:return
    if y0==y1:
        if 0<=y0<h:
            a,b=sorted((x0,x1));a=max(0,a);b=min(w-1,b)
            if a<=b:index[y0,a:b+1]=color
        return
    if x0==x1:
        if 0<=x0<w:
            a,b=sorted((y0,y1));a=max(0,a);b=min(h-1,b)
            if a<=b:index[a:b+1,x0]=color
        return
    dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
    x,y=x0,y0
    while True:
        if 0<=x<w and 0<=y<h:index[y,x]=color
        if x==x1 and y==y1:break
        e2=2*err
        if e2>=dy:err+=dy;x+=sx
        if e2<=dx:err+=dx;y+=sy


def pixel_map_from_groups(image: Image.Image, groups, palette_rgb: Sequence[Sequence[int]], *,
                          cancelled=lambda: False) -> PixelMap:
    """Reconstruct the exact quantized target raster from already-built groups."""
    w,h=map(int,image.size)
    index=np.full((h,w),-1,dtype=np.int16)
    for ci,strokes in enumerate(groups or ()):
        for n,stroke in enumerate(strokes or ()):
            if n%512==0:_cancel(cancelled)
            _raster_line(index,ci,stroke)
    drawable=index>=0
    palette=np.asarray([tuple(map(int,c[:3])) for c in palette_rgb],dtype=np.uint8)
    rgb=np.full((h,w,3),255,dtype=np.uint8)
    if len(palette):
        yy,xx=np.nonzero(drawable)
        if len(yy):
            safe=np.clip(index[yy,xx],0,len(palette)-1)
            rgb[yy,xx]=palette[safe]

    edge=np.zeros((h,w),dtype=np.float32)
    if w>1:
        diff=(index[:,1:]!=index[:,:-1]) & (drawable[:,1:]|drawable[:,:-1])
        edge[:,1:]=np.maximum(edge[:,1:],diff)
        edge[:,:-1]=np.maximum(edge[:,:-1],diff)
    if h>1:
        diff=(index[1:,:]!=index[:-1,:]) & (drawable[1:,:]|drawable[:-1,:])
        edge[1:,:]=np.maximum(edge[1:,:],diff)
        edge[:-1,:]=np.maximum(edge[:-1,:],diff)

    source_edge=np.zeros_like(edge)
    route_meta={}
    try:
        from UniversalGpuAcceleration import edge_magnitude
        visible=np.asarray(image.convert("RGB"),dtype=np.float32)
        lum=(visible[...,0]*.2126+visible[...,1]*.7152+visible[...,2]*.0722)/255.0
        source_edge,route=edge_magnitude(lum,gpu_mode="Auto",cancelled=cancelled)
        source_edge=np.asarray(source_edge,dtype=np.float32)
        if source_edge.shape!=edge.shape:source_edge=np.zeros_like(edge)
        source_edge=np.clip(source_edge/max(.001,float(np.percentile(source_edge,95)) if source_edge.size else 1.0),0,1)
        route_meta=route if isinstance(route,dict) else getattr(route,"as_dict",lambda:{})()
    except Exception:
        pass
    edge=np.maximum(edge,source_edge*.72).astype(np.float32,copy=False)

    neighbours=np.zeros((h,w),dtype=np.uint8)
    neighbours[1:,:]+=drawable[:-1,:];neighbours[:-1,:]+=drawable[1:,:]
    neighbours[:,1:]+=drawable[:,:-1];neighbours[:,:-1]+=drawable[:,1:]
    micro=drawable & ((neighbours<=2)|(edge>=.78))
    importance=np.where(drawable,.18,0.0).astype(np.float32)
    importance += edge*.58
    importance += micro.astype(np.float32)*.24
    importance=np.clip(importance,0,1)
    protected=drawable & ((edge>=.62)|micro)
    return PixelMap(w,h,rgb,index,drawable,edge,importance,protected,{
        "engine":"Adaptive Region Hybrid target raster","source":"existing quantized groups",
        "gpu_edge_route":route_meta,"drawable_pixels":int(np.count_nonzero(drawable)),
    },contour_map=edge,micro_detail_map=micro.astype(np.float32))


def _individual_paths(runs):
    out=[]
    for x0,y0,x1,y1 in runs:
        out.append(((int(x0),int(y0)),) if (x0,y0)==(x1,y1) else ((int(x0),int(y0)),(int(x1),int(y1))))
    return out


def _orientation_paths(comp, orientation: str, component_map: np.ndarray, cancelled=lambda: False):
    """Reuse PixelStrokeEngine's verified lossless merger for one forced orientation."""
    from PixelStrokeEngine import (
        _merge_horizontal_runs_lossless, _transpose_segments, _transpose_paths,
        _path_inside_component, _paths_exact_component_coverage,
    )
    runs=comp.horizontal_runs if orientation=="horizontal" else comp.vertical_runs
    if orientation=="horizontal":
        paths=_merge_horizontal_runs_lossless(runs,cancelled=cancelled)
    else:
        paths=_transpose_paths(_merge_horizontal_runs_lossless(_transpose_segments(runs),cancelled=cancelled))
    exact=all(_path_inside_component(p,component_map,comp.component_id) for p in paths)
    exact=exact and _paths_exact_component_coverage(paths,component_map,comp)
    if not exact:
        paths=_individual_paths(runs)
        exact=all(_path_inside_component(p,component_map,comp.component_id) for p in paths)
        exact=exact and _paths_exact_component_coverage(paths,component_map,comp)
    return list(paths),bool(exact)


def _phase(comp,total_drawable:int) -> str:
    ratio=comp.area/max(1,total_drawable)
    if ratio>=.015 and comp.edge_mean<.42 and comp.protected_ratio<.10:return "foundation"
    if comp.contour_mean>=.48 or comp.edge_mean>=.52 or comp.importance_mean>=.52:return "structure"
    if comp.protected_pixels or comp.area<=24:return "detail"
    return "structure" if comp.importance_mean>=.38 else "correction"


def _component_gain(comp,total_drawable:int) -> float:
    area=comp.area/max(1,total_drawable)
    structural=min(1.0,comp.edge_mean*.72+comp.contour_mean*.48+comp.protected_ratio*.75)
    detail=min(1.0,comp.importance_mean*.72+comp.importance_max*.28)
    return max(.00001,area*(.58+.42*detail)+structural*.012+min(comp.area,64)/max(1,total_drawable)*.22)


def _entry_sequence(color_index:int, paths, *, phase:str, comp, brush_px:int, method:str):
    out=[]
    for serial,path in enumerate(paths):
        out.append({
            "color_index":int(color_index),"path":tuple(path),"phase":phase,
            "phase_label":phase.replace("_"," "),"component_id":int(comp.component_id),
            "component_area":int(comp.area),"component_width":int(comp.width),"component_height":int(comp.height),
            "importance":round(float(comp.importance_max),6),"protected":bool(comp.protected_pixels),
            "edge_mean":round(float(comp.edge_mean),6),"contour_mean":round(float(comp.contour_mean),6),
            "brush_px":int(brush_px),"hybrid_method":method,"local_serial":serial,
        })
    return out


def _paint_path(mask:np.ndarray,path,brush_px:int):
    h,w=mask.shape;b=max(1,int(brush_px));lo=(b-1)//2;hi=b//2
    def rect(x0,y0,x1,y1):
        xa=max(0,min(x0,x1)-lo);xb=min(w-1,max(x0,x1)+hi)
        ya=max(0,min(y0,y1)-lo);yb=min(h-1,max(y0,y1)+hi)
        if xa<=xb and ya<=yb:mask[ya:yb+1,xa:xb+1]=True
    pts=list(path or ())
    if not pts:return
    if len(pts)==1:
        x,y=map(int,pts[0]);rect(x,y,x,y);return
    for a,bp in zip(pts,pts[1:]):
        x0,y0=map(int,a);x1,y1=map(int,bp)
        if x0==x1 or y0==y1:rect(x0,y0,x1,y1)
        else:
            steps=max(abs(x1-x0),abs(y1-y0),1)
            for i in range(steps+1):
                t=i/steps;x=round(x0+(x1-x0)*t);y=round(y0+(y1-y0)*t);rect(x,y,x,y)


def _eroded_centers(target:np.ndarray,brush_px:int) -> np.ndarray:
    b=max(1,int(brush_px));lo=(b-1)//2;hi=b//2
    valid=np.ones_like(target)
    h,w=target.shape
    for dy in range(-lo,hi+1):
        for dx in range(-lo,hi+1):
            shifted=np.zeros_like(target)
            ys=slice(max(0,-dy),min(h,h-dy));yd=slice(max(0,dy),min(h,h+dy))
            xs=slice(max(0,-dx),min(w,w-dx));xd=slice(max(0,dx),min(w,w+dx))
            shifted[yd,xd]=target[ys,xs]
            valid &= shifted
    return valid


def _runs_from_mask(mask:np.ndarray,row_stride:int=1):
    h,w=mask.shape;out=[]
    stride=max(1,int(row_stride))
    for y in range(0,h,stride):
        row=mask[y];x=0
        while x<w:
            if not row[x]:x+=1;continue
            x0=x;x+=1
            while x<w and row[x]:x+=1
            out.append(((x0,y),(x-1,y)) if x-1!=x0 else ((x0,y),))
    return out


def _broad_brush_candidate(comp,component_map,options,model,cancelled=lambda:False):
    default=max(1,int(options.get("brush_px") or 1))
    sizes,dynamic=verified_brush_sizes(str(options.get("profile_key") or ""),
                                       options.get("browser_brush_plan"),default)
    if not dynamic or len(sizes)<2 or min(sizes)!=1:
        return None,"no verified 1px + broad brush controls"
    broad=max(sizes)
    if broad<=1 or comp.area<max(96,broad*broad*6):
        return None,"component too small for broad brush"
    target=component_map==comp.component_id
    centers=_eroded_centers(target,broad)
    if not np.any(centers):return None,"no safe broad-brush interior"
    broad_paths=_runs_from_mask(centers,row_stride=max(1,broad))
    painted=np.zeros_like(target)
    for path in broad_paths:_paint_path(painted,path,broad)
    if np.any(painted & ~target):return None,"broad brush spills outside component"
    residual=target & ~painted
    detail_paths=_runs_from_mask(residual,1)
    for path in detail_paths:_paint_path(painted,path,1)
    if np.any(painted & ~target) or not np.array_equal(painted,target):
        return None,"broad+detail simulation is not exact"
    seq=_entry_sequence(comp.color_index,broad_paths,phase=_phase(comp,int(np.count_nonzero(component_map>=0))),
                        comp=comp,brush_px=broad,method="broad-brush-interior")
    seq += _entry_sequence(comp.color_index,detail_paths,phase="detail",comp=comp,brush_px=1,method="narrow-edge-repair")
    cost=model.sequence_cost(seq).total_seconds
    return {"sequence":seq,"paths":broad_paths+detail_paths,"cost":cost,"brush_px":broad,
            "method":"broad+narrow","exact":True}, "safe simulated broad interior + 1px repair"


def _choose_component(comp,component_map,total_drawable,model,options,cancelled=lambda:False):
    phase=_phase(comp,total_drawable);gain=_component_gain(comp,total_drawable)
    candidates=[]
    for orientation in ("horizontal","vertical"):
        paths,exact=_orientation_paths(comp,orientation,component_map,cancelled)
        if not exact:continue
        seq=_entry_sequence(comp.color_index,paths,phase=phase,comp=comp,
                            brush_px=max(1,int(options.get("brush_px") or 1)),
                            method=f"connected-{orientation}-runs")
        cost=model.sequence_cost(seq).total_seconds
        candidates.append((cost,len(paths),orientation,seq,paths,max(1,int(options.get("brush_px") or 1))))
    broad,broad_reason=_broad_brush_candidate(comp,component_map,options,model,cancelled)
    if broad:
        candidates.append((broad["cost"],len(broad["paths"]),broad["method"],broad["sequence"],broad["paths"],broad["brush_px"]))
    if comp.area==1:
        x0,y0,_,_=comp.bbox;paths=[((x0,y0),)]
        seq=_entry_sequence(comp.color_index,paths,phase="detail",comp=comp,brush_px=1,method="isolated-point")
        candidates.append((model.sequence_cost(seq).total_seconds,1,"isolated-point",seq,paths,1))
    if not candidates:
        paths=_individual_paths(comp.horizontal_runs)
        seq=_entry_sequence(comp.color_index,paths,phase=phase,comp=comp,
                            brush_px=max(1,int(options.get("brush_px") or 1)),method="safe-individual-runs")
        candidates=[(model.sequence_cost(seq).total_seconds,len(paths),"safe-individual-runs",seq,paths,max(1,int(options.get("brush_px") or 1)))]
    best=min(candidates,key=lambda row:(row[0],row[1],row[2]))
    cost=max(.000001,float(best[0]))
    choice=RegionChoice(comp.component_id,comp.color_index,best[2],phase,comp.area,
                        float(comp.importance_mean),float(comp.edge_mean),comp.protected_pixels,
                        cost,gain,gain/(cost*1000.0),best[1],best[5],True,
                        f"minimum calibrated execution cost among {len(candidates)} exact candidate(s); {broad_reason}")
    return choice,list(best[3]),{
        "component_id":comp.component_id,
        "candidates":[{"method":c[2],"estimated_seconds":round(float(c[0]),6),"paths":int(c[1])} for c in candidates],
    }


def _budget_seconds(options,model,choices,fill_regions):
    active=bool(options.get("time_budget_active"))
    mode=str(options.get("time_budget_mode") or "")
    if mode in ("Unlimited","Off"):active=False
    try:limit=float(options.get("max_seconds") or options.get("manual_max_seconds") or 180)
    except Exception:limit=180.0
    colors=len({c.color_index for c in choices})
    fixed=model.fixed_overhead(active_colors=colors,fill_actions=len(fill_regions))
    reserve=max(1.5,limit*.045) if active else 0.0
    return active,max(0.0,limit-fixed.total_seconds-reserve),fixed,reserve,limit


def _schedule(choices, sequences_by_component, size, model,options,fill_regions):
    active,usable,fixed,reserve,limit=_budget_seconds(options,model,choices,fill_regions)
    if not active:
        selected={c.component_id for c in choices}
    else:
        selected=set();used=0.0
        cell_best={}
        for c in choices:
            seq=sequences_by_component[c.component_id]
            pts=[p for e in seq for p in (e.get("path") or ())[:1]]
            if not pts:continue
            x,y=pts[0];cx=min(3,max(0,int(x/max(1,size[0])*4)));cy=min(3,max(0,int(y/max(1,size[1])*4)))
            old=cell_best.get((cx,cy))
            if old is None or (c.visual_gain,c.area,-c.component_id)>(old.visual_gain,old.area,-old.component_id):
                cell_best[(cx,cy)]=c
        for c in sorted(cell_best.values(),key=lambda c:(-c.visual_gain,c.component_id)):
            if used+c.estimated_seconds<=usable:
                selected.add(c.component_id);used+=c.estimated_seconds
        weights={"foundation":1.25,"structure":1.18,"detail":1.04,"correction":.78}
        rest=[c for c in choices if c.component_id not in selected]
        rest.sort(key=lambda c:(-(c.gain_per_ms*weights[c.phase]),-c.visual_gain,c.component_id))
        for c in rest:
            if used+c.estimated_seconds<=usable:
                selected.add(c.component_id);used+=c.estimated_seconds
    phase_order={p:i for i,p in enumerate(PHASES)}
    selected_choices=[c for c in choices if c.component_id in selected]
    selected_choices.sort(key=lambda c:(phase_order[c.phase],-c.gain_per_ms,-c.visual_gain,c.component_id))
    sequence=[];serial=0
    for c in selected_choices:
        for raw in sequences_by_component[c.component_id]:
            e=dict(raw);e["serial"]=serial;serial+=1;sequence.append(e)
    groups=[[] for _ in range(max([c.color_index for c in choices],default=-1)+1)]
    for e in sequence:
        while len(groups)<=int(e["color_index"]):groups.append([])
        groups[int(e["color_index"])].append(tuple(e["path"]))
    seq_cost=model.sequence_cost(sequence)
    return groups,sequence,{
        "deadline_active":active,"deadline_seconds":round(limit,4),"usable_path_seconds":round(usable,4),
        "fixed_overhead":fixed.as_dict(),"safety_reserve_seconds":round(reserve,4),
        "selected_components":len(selected),"total_components":len(choices),
        "dropped_components":len(choices)-len(selected),
        "selected_path_cost_seconds":round(seq_cost.total_seconds,6),
        "selected_operation_cost":seq_cost.as_dict(),
    }


def simulate_quantized_plan(pixel_map:PixelMap,sequence,fill_regions=()):
    h,w=pixel_map.height,pixel_map.width
    canvas=np.full((h,w),-1,dtype=np.int16)
    for region in fill_regions or ():
        try:ci=int(region.get("color_index"))
        except Exception:continue
        for raw in region.get("row_spans") or ():
            try:y,x0,x1=map(int,raw)
            except Exception:continue
            if 0<=y<h:
                if x1<x0:x0,x1=x1,x0
                x0=max(0,x0);x1=min(w-1,x1)
                if x0<=x1:canvas[y,x0:x1+1]=ci
    for e in sequence or ():
        try:ci=int(e["color_index"]);brush=max(1,int(e.get("brush_px") or 1))
        except Exception:continue
        mask=np.zeros((h,w),dtype=np.bool_)
        _paint_path(mask,e.get("path") or (),brush)
        canvas[mask]=ci
    target=pixel_map.palette_index;drawable=pixel_map.drawable_mask
    intended=max(1,int(np.count_nonzero(drawable)))
    painted=canvas>=0
    correct=drawable & (canvas==target)
    covered=drawable & painted
    wrong=drawable & painted & (canvas!=target)
    spill=(~drawable)&painted
    edge_target=drawable & (pixel_map.edge_map>=.5)
    protected=drawable & pixel_map.protected_mask
    def pct(n,d):return float(n)/max(1,int(d))*100.0
    coverage=pct(np.count_nonzero(covered),intended)
    color=pct(np.count_nonzero(correct),intended)
    edge=pct(np.count_nonzero(correct & edge_target),np.count_nonzero(edge_target))
    detail=pct(np.count_nonzero(correct & protected),np.count_nonzero(protected))
    spill_acc=max(0.0,100.0-pct(np.count_nonzero(spill),max(1,np.count_nonzero(painted))))
    score=.35*color+.25*coverage+.20*edge+.15*detail+.05*spill_acc
    return {
        "coverage_percent":round(coverage,4),"color_accuracy_percent":round(color,4),
        "edge_preservation_percent":round(edge,4),"protected_detail_percent":round(detail,4),
        "spill_accuracy_percent":round(spill_acc,4),"wrong_color_pixels":int(np.count_nonzero(wrong)),
        "spill_pixels":int(np.count_nonzero(spill)),"missing_pixels":int(np.count_nonzero(drawable & ~painted)),
        "pixel_accuracy_score":round(score,4),
        "score_formula":"0.35*color_accuracy + 0.25*coverage + 0.20*edge_preservation + 0.15*protected_detail + 0.05*spill_accuracy",
    },canvas


def diagnostic_previews(pixel_map:PixelMap,canvas:np.ndarray):
    h,w=canvas.shape
    coverage=np.zeros((h,w,3),dtype=np.uint8)
    coverage[:]=255
    target=pixel_map.palette_index;drawable=pixel_map.drawable_mask
    correct=drawable&(canvas==target);missing=drawable&(canvas<0);wrong=drawable&(canvas>=0)&(canvas!=target);spill=(~drawable)&(canvas>=0)
    coverage[correct]=(225,225,225);coverage[missing]=(255,80,80);coverage[wrong]=(255,170,45);coverage[spill]=(175,60,220)
    error=coverage.copy()
    return Image.fromarray(coverage,"RGB"),Image.fromarray(error,"RGB")


def build_adaptive_execution(pixel_map:PixelMap,palette_rgb,options:dict[str,Any],fitted,
                             *,fill_regions=(),reference_pixel_map:PixelMap|None=None,cancelled=lambda:False):
    t0=time.perf_counter();_cancel(cancelled)
    workers=max(1,int(options.get("cpu_workers_resolved") or 1))
    components,cmap,component_meta=connected_components(pixel_map,cpu_workers=workers,cancelled=cancelled)
    region_seconds=time.perf_counter()-t0
    model=build_cost_model(options,(pixel_map.width,pixel_map.height),tuple(fitted))
    total=max(1,int(np.count_nonzero(pixel_map.drawable_mask)))
    choices=[];seqs={};candidate_meta=[]
    t1=time.perf_counter()
    for comp in components:
        _cancel(cancelled)
        choice,seq,meta=_choose_component(comp,cmap,total,model,options,cancelled)
        choices.append(choice);seqs[comp.component_id]=seq;candidate_meta.append(meta)
    candidate_seconds=time.perf_counter()-t1
    t2=time.perf_counter()
    groups,sequence,schedule_meta=_schedule(choices,seqs,(pixel_map.width,pixel_map.height),model,options,fill_regions)
    reference=reference_pixel_map if reference_pixel_map is not None else pixel_map
    metrics,canvas=simulate_quantized_plan(reference,sequence,fill_regions)
    coverage_preview,error_preview=diagnostic_previews(reference,canvas)
    simulation_seconds=time.perf_counter()-t2
    methods={}
    for c in choices:methods[c.method]=methods.get(c.method,0)+1
    return {
        "execution_groups":groups,"execution_sequence":sequence,
        "metrics":metrics,"coverage_preview":coverage_preview,"error_preview":error_preview,
        "metadata":{
            "enabled":True,"version":ADAPTIVE_HYBRID_VERSION,"engine":"Adaptive Region Hybrid 4.0",
            "component_meta":component_meta,"components":len(components),"methods":methods,
            "region_choices":[c.as_dict() for c in choices[:256]],
            "candidate_diagnostics":candidate_meta[:128],"schedule":schedule_meta,
            "cost_model":{"source":model.source,"measured_samples":model.samples,"calibration_ratio":round(model.multiplier,6),
                          "profile_key":str(options.get("profile_key") or ""), "stroke_delivery":model.delivery.as_dict()},
            "timings":{"region_analysis_seconds":round(region_seconds,6),
                       "candidate_scoring_seconds":round(candidate_seconds,6),
                       "plan_simulation_seconds":round(simulation_seconds,6),
                       "adaptive_hybrid_total_seconds":round(time.perf_counter()-t0,6)},
            "quality":metrics,
            "fallback_engine":"legacy standard planner",
            "native_input_engine_changed":False,
        },
    }


def _build_fill_regions(groups,palette_rgb,image_size,fitted,options,cancelled):
    if not options.get("fill_tool_available"):
        return [],{"enabled":False,"reason":"target has no verified Fill capability"}
    try:
        from FillOptimizer import detect_fill_regions_from_groups
        from RegionFillEngine import evaluate_region_candidates
        from SafeFillMask import filter_fill_regions_by_source_mask,source_fill_margin_px
        mode=str(options.get("background_fill") or "Balanced")
        if mode=="Off":mode="Balanced"
        margin=source_fill_margin_px(options.get("brush_px",1),2,image_size)
        candidates,base=detect_fill_regions_from_groups(
            groups,palette_rgb,image_size,mode,engine=options.get("fill_engine","Closed regions v2"),
            max_regions=384,cancelled=cancelled,return_meta=True,safe_margin_px=margin)
        accepted,meta=evaluate_region_candidates(candidates,image_size,fitted,options,base_meta=base,cancelled=cancelled)
        accepted,mask_meta=filter_fill_regions_by_source_mask(accepted,image_size,margin_px=margin)
        accepted,state_meta=filter_stateful_fill_regions(accepted,image_size,brush_px=max(1,int(options.get("brush_px") or 1)),cancelled=cancelled)
        meta=dict(meta);meta["safe_fill_mask"]=mask_meta;meta["stateful_fill_simulation"]=state_meta
        meta["fill_safe_regions"]=len(accepted);meta["fill_actions"]=len(accepted)
        return list(accepted),meta
    except InterruptedError:raise
    except Exception as exc:
        return [],{"enabled":True,"fill_safe_regions":0,"fallback":"connected runs","reason":f"{type(exc).__name__}: {exc}"}


def _strokes_from_paths(groups):
    out=[]
    for paths in groups or ():
        strokes=[]
        for path in paths or ():
            pts=list(path)
            if not pts:continue
            if len(pts)==1:
                x,y=pts[0];strokes.append((int(x),int(y),int(x),int(y)));continue
            strokes.extend((int(a[0]),int(a[1]),int(b[0]),int(b[1])) for a,b in zip(pts,pts[1:]) if a!=b)
        out.append(strokes)
    return out


def build_adaptive_hybrid_plan(original:Image.Image,area,options:dict[str,Any],make_plan,finish_plan,
                               cancelled:Callable[[],bool]=lambda:False):
    """Build through the existing color engine, then replace only safe geometry."""
    if options.get("erase_mode"):
        raise ValueError("Adaptive Hybrid 4.0 needs a drawing tool, not Eraser.")
    inner=dict(options)
    inner.update({
        "_adaptive_hybrid_inner":True,"auto_engine_resolved":True,
        "render_style":"Standard / pixel","outline":False,
        "background_fill":"Off","use_region_fill_engine":False,
        "fill_tool_available":False,"progressive_rendering":"Off","stroke_optimizer":"Off",
        "detail_zoom":"Off",
    })
    inner.pop("background_fill_plan",None);inner.pop("fill_regions",None)
    base=make_plan(original,area,inner,cancelled)
    _cancel(cancelled)
    try:
        groups=[list(g) for g in (base.get("groups") or ())]
        palette=tuple(base.get("colors") or ())
        if not groups or not palette:
            raise ValueError("base color planner produced no drawable groups/palette")
        outer=dict(base.get("options") or {})
        for key in ("fill_tool_available","fill_tool_actions","fill_restore_actions","background_fill",
                    "fill_engine","fill_aggressiveness","use_region_fill_engine","browser_brush_plan",
                    "paint_profile","profile_key","profile_name","brush_px","time_budget_active",
                    "time_budget_mode","max_seconds","manual_max_seconds","deadline_safety_reserve"):
            if key in options:outer[key]=options[key]
        fill_regions,fill_meta=_build_fill_regions(groups,palette,base["image"].size,base["fitted"],outer,cancelled)
        reference_pixel_map=pixel_map_from_groups(base["image"],groups,palette,cancelled=cancelled)
        work_groups=groups
        if fill_regions:
            from FillOptimizer import remove_filled_region_strokes
            work_groups=remove_filled_region_strokes(work_groups,fill_regions)
        pixel_map=pixel_map_from_groups(base["image"],work_groups,palette,cancelled=cancelled)
        result=build_adaptive_execution(pixel_map,palette,outer,base["fitted"],fill_regions=fill_regions,
                                        reference_pixel_map=reference_pixel_map,cancelled=cancelled)
        outer.update({
            "render_style":ADAPTIVE_HYBRID_RENDER_STYLE,"adaptive_hybrid_active":True,
            "adaptive_hybrid_version":ADAPTIVE_HYBRID_VERSION,"fill_regions":fill_regions,
            "region_fill_meta":fill_meta,"stroke_optimizer":"Off","progressive_rendering":"On",
            "color_workflow":"Progressive passes",
            "_adaptive_hybrid_execution_groups":result["execution_groups"],
            "_adaptive_hybrid_execution_sequence":result["execution_sequence"],
            "_pixel_coverage_preview":result["coverage_preview"],
            "_pixel_error_preview":result["error_preview"],
            "adaptive_hybrid_meta":result["metadata"],
            "_accuracy_original_source":original.copy(),
        })
        outer.pop("background_fill_plan",None)
        final_groups=_strokes_from_paths(result["execution_groups"])
        plan=finish_plan(base["image"],base["fitted"],final_groups,outer,cancelled)
        plan.setdefault("adaptive_hybrid_meta",result["metadata"])
        return plan
    except InterruptedError:raise
    except Exception as exc:
        base.setdefault("options",{})["adaptive_hybrid_meta"]={
            "enabled":False,"fallback":True,"fallback_engine":"legacy standard planner",
            "reason":f"{type(exc).__name__}: {exc}","native_input_engine_changed":False}
        base["adaptive_hybrid_meta"]=dict(base["options"]["adaptive_hybrid_meta"])
        return base


def render_adaptive_preview(source_size,preview_size,sequence,palette_rgb,fill_regions=()):
    w,h=map(int,source_size);pw,ph=map(int,preview_size)
    out=Image.new("RGB",(max(1,pw),max(1,ph)),"white");draw=ImageDraw.Draw(out)
    sx=pw/max(1,w);sy=ph/max(1,h)
    for region in fill_regions or ():
        try:color=tuple(map(int,palette_rgb[int(region["color_index"])]))
        except Exception:continue
        for raw in region.get("row_spans") or ():
            try:y,x0,x1=map(int,raw)
            except Exception:continue
            draw.rectangle((x0*sx,y*sy,(x1+1)*sx,max((y+1)*sy,y*sy+1)),fill=color)
    for entry in sequence or ():
        try:color=tuple(map(int,palette_rgb[int(entry["color_index"])]));brush=max(1,int(entry.get("brush_px") or 1))
        except Exception:continue
        pts=[(float(x)*sx,float(y)*sy) for x,y in (entry.get("path") or ())]
        if not pts:continue
        width=max(1,int(round(brush*(sx+sy)*.5)))
        if len(pts)==1:
            x,y=pts[0];r=max(.5,width/2);draw.rectangle((x-r,y-r,x+r,y+r),fill=color)
        else:draw.line(pts,fill=color,width=width,joint="curve")
    return out
