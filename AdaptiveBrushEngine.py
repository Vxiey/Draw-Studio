"""Adaptive brush policy for Image Draw Bot v1.0.90-beta.

The Pixel Accurate planner keeps source geometry lossless, then this module
assigns a physically executable brush width to every path. It only enables
multi-size browser drawing when the read-only BrowserBrushSize preflight
verified every control position. No mouse input occurs here.
"""
from __future__ import annotations

from collections import Counter
from typing import Sequence


def _unique_sizes(values, fallback: int) -> tuple[int, ...]:
    out=[]
    for value in values or ():
        try:v=max(1,int(round(float(value))))
        except (TypeError,ValueError):continue
        if v not in out:out.append(v)
    if not out:out=[max(1,int(fallback))]
    return tuple(sorted(out))


def verified_brush_sizes(profile_key: str, browser_brush_plan: dict | None, default_brush_px: int) -> tuple[tuple[int,...], bool]:
    default=max(1,int(default_brush_px or 1));plan=browser_brush_plan if isinstance(browser_brush_plan,dict) else {}
    sizes=_unique_sizes(plan.get('nominal_sizes'),default)
    positions=plan.get('control_positions') or ()
    try:confidence=float(plan.get('confidence',0) or 0)
    except (TypeError,ValueError):confidence=0.0
    verified=bool(plan.get('target_position')) and confidence>=.58 and len(positions)==len(sizes) and len(sizes)>1
    usable=tuple(v for v in sizes if v<=default) or (default,)
    if not verified:return (default,),False
    return usable,True


def _nearest_not_above(sizes: Sequence[int], wanted: int) -> int:
    wanted=max(1,int(wanted));below=[int(v) for v in sizes if int(v)<=wanted]
    return max(below) if below else min(map(int,sizes))


def assign_adaptive_brushes(execution_sequence: Sequence[dict], *, profile_key: str = '',
                            default_brush_px: int = 1, browser_brush_plan: dict | None = None) -> dict:
    default=max(1,int(default_brush_px or 1))
    sizes,dynamic=verified_brush_sizes(profile_key,browser_brush_plan,default)
    smallest=min(sizes);base=_nearest_not_above(sizes,default)
    if len(sizes)>=2:
        lower=[v for v in sizes if v<base]
        middle=max(lower) if lower else smallest
    else:middle=base
    result=[];reasons=Counter();counts=Counter();previous=None;switches=0
    for raw in execution_sequence:
        entry=dict(raw);phase=str(entry.get('phase') or 'fine_detail').rsplit('/',1)[-1]
        protected=bool(entry.get('protected'))
        try:importance=float(entry.get('importance',0) or 0)
        except (TypeError,ValueError):importance=0.0
        try:w=int(entry.get('component_width',0) or 0);h=int(entry.get('component_height',0) or 0)
        except (TypeError,ValueError):w=h=0
        path=entry.get('path') or ();turns=max(0,len(path)-2)
        brush=base;reason='base'
        if not dynamic:
            brush=base;reason='fixed-unverified-controls'
        elif phase.startswith('correction_'):
            brush=smallest;reason='accuracy-correction'
        elif phase=='cleanup' or protected:
            brush=smallest;reason='protected-detail'
        elif phase=='fine_detail':
            brush=smallest;reason='fine-detail'
        elif phase=='mid_detail':
            thin=min(v for v in (w,h) if v>0) if w>0 and h>0 else 999999
            if thin<=max(3,base*2) or importance>=.58 or turns>=2:
                brush=smallest;reason='edge-sensitive-mid-detail'
            else:
                brush=middle;reason='mid-detail'
        else:
            brush=base;reason='large-fill'
        brush=int(max(1,brush));entry['brush_px']=brush;entry['brush_reason']=reason
        counts[brush]+=1;reasons[reason]+=1
        if previous is not None and brush!=previous:switches+=1
        previous=brush;result.append(entry)
    return {'execution_sequence':result,'metadata':{
        'engine':'Adaptive Brush Draw Motor v2','dynamic_brush_enabled':bool(dynamic),
        'profile_key':str(profile_key or ''),'available_brush_sizes':tuple(map(int,sizes)),
        'default_brush_px':base,'detail_brush_px':smallest,'mid_brush_px':middle,
        'brush_path_counts':{str(k):int(v) for k,v in sorted(counts.items())},
        'brush_reason_counts':dict(reasons),'planned_brush_switches':int(switches),
        'geometry_changed':False,'quality_priority':'detail paths use smallest verified browser brush'}}


def brush_for_entry(entry: dict, default_brush_px: int) -> int:
    try:return max(1,int(entry.get('brush_px',default_brush_px) or default_brush_px))
    except (TypeError,ValueError,AttributeError):return max(1,int(default_brush_px or 1))
