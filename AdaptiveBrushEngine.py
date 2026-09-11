"""Adaptive brush policy for Image Draw Bot.

The planner keeps source geometry authoritative, then this module assigns a
physically executable brush width to every path. Multi-size drawing is enabled
only when BrowserBrushSize verified the target controls. The automatic selector
uses planned image geometry (detail density, protected features, component
thickness and path complexity) to choose a safe base brush, while corrections
and small details always use the smallest verified brush. No mouse input occurs
here.
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


def _plan_confidence(plan: dict) -> float:
    try:return float(plan.get('confidence',0) or 0)
    except (TypeError,ValueError):return 0.0


def verified_brush_sizes(profile_key: str, browser_brush_plan: dict | None,
                         default_brush_px: int) -> tuple[tuple[int,...], bool]:
    """Return only brush sizes whose UI controls and safety inset were verified.

    Older plans do not expose ``safe_guard_px``; for those plans the historic
    behavior is preserved and the manual/default brush remains the upper bound.
    Newer browser preflight plans may expose a larger verified guard, which lets
    Auto Brush use a broader preset without weakening CanvasGuard.
    """
    default=max(1,int(default_brush_px or 1))
    plan=browser_brush_plan if isinstance(browser_brush_plan,dict) else {}
    sizes=_unique_sizes(plan.get('nominal_sizes'),default)
    positions=plan.get('control_positions') or ()
    confidence=_plan_confidence(plan)
    verified=bool(plan.get('target_position')) and confidence>=.58 and len(positions)==len(sizes) and len(sizes)>1
    if not verified:
        return (default,),False
    try:safe_guard=max(default,int(round(float(plan.get('safe_guard_px',default) or default))))
    except (TypeError,ValueError):safe_guard=default
    usable=tuple(v for v in sizes if v<=safe_guard)
    if not usable:
        usable=(default,)
    return usable,True


def _nearest_not_above(sizes: Sequence[int], wanted: int) -> int:
    wanted=max(1,int(wanted));below=[int(v) for v in sizes if int(v)<=wanted]
    return max(below) if below else min(map(int,sizes))


def _safe_float(value, default=0.0) -> float:
    try:return float(value)
    except (TypeError,ValueError):return float(default)


def _component_thin(entry: dict) -> int | None:
    try:
        w=max(0,int(entry.get('component_width',0) or 0))
        h=max(0,int(entry.get('component_height',0) or 0))
    except (TypeError,ValueError,AttributeError):
        return None
    dims=[v for v in (w,h) if v>0]
    return min(dims) if dims else None


def analyze_brush_demand(execution_sequence: Sequence[dict]) -> dict:
    """Classify the planned image geometry for automatic brush selection.

    This intentionally analyzes planner output rather than re-reading pixels, so
    preview and final rendering use the same source of truth and no extra image
    buffer is allocated.
    """
    total=0
    detail=protected=high_importance=turn_heavy=narrow=large_foundation=0
    importance_sum=0.0
    thin_values=[]
    for raw in execution_sequence or ():
        if not isinstance(raw,dict):
            continue
        total+=1
        phase=str(raw.get('phase') or 'fine_detail').rsplit('/',1)[-1]
        is_protected=bool(raw.get('protected'))
        importance=max(0.0,min(1.0,_safe_float(raw.get('importance',0),0)))
        path=raw.get('path') or ()
        turns=max(0,len(path)-2)
        thin=_component_thin(raw)
        try:area=max(0,int(raw.get('component_area',0) or 0))
        except (TypeError,ValueError):area=0

        if phase in ('fine_detail','cleanup') or phase.startswith('correction_'):
            detail+=1
        if is_protected:
            protected+=1
        if importance>=.58:
            high_importance+=1
        if turns>=2:
            turn_heavy+=1
        if thin is not None:
            thin_values.append(thin)
            if thin<=6:narrow+=1
        if phase in ('fill','foundation','base') and area>=128 and importance<.58 and not is_protected:
            large_foundation+=1
        importance_sum+=importance

    if total<=0:
        return {
            'classification':'balanced','detail_score':0.5,'flat_score':0.0,
            'paths':0,'detail_ratio':0.0,'protected_ratio':0.0,
            'narrow_ratio':0.0,'turn_ratio':0.0,'mean_importance':0.0,
            'large_foundation_ratio':0.0,'median_thin_px':None,
        }
    detail_ratio=detail/total
    protected_ratio=protected/total
    high_ratio=high_importance/total
    turn_ratio=turn_heavy/total
    narrow_ratio=narrow/total
    foundation_ratio=large_foundation/total
    mean_importance=importance_sum/total
    median_thin=None
    if thin_values:
        ordered=sorted(thin_values);median_thin=ordered[len(ordered)//2]

    detail_score=min(1.0,
        detail_ratio*.34 + protected_ratio*.22 + high_ratio*.18 +
        turn_ratio*.10 + narrow_ratio*.10 + mean_importance*.06)
    flat_score=min(1.0,
        foundation_ratio*.72 + max(0.0,.45-detail_score)*.62)
    if detail_score>=.48:
        classification='detail-heavy'
    elif flat_score>=.42 and detail_score<=.30:
        classification='flat-shape'
    else:
        classification='balanced'
    return {
        'classification':classification,
        'detail_score':round(detail_score,4),'flat_score':round(flat_score,4),
        'paths':int(total),'detail_ratio':round(detail_ratio,4),
        'protected_ratio':round(protected_ratio,4),'narrow_ratio':round(narrow_ratio,4),
        'turn_ratio':round(turn_ratio,4),'mean_importance':round(mean_importance,4),
        'large_foundation_ratio':round(foundation_ratio,4),
        'median_thin_px':median_thin,
    }


def _select_auto_levels(sizes: Sequence[int], default: int, demand: dict,
                        *, dynamic: bool) -> tuple[int,int,int,str]:
    values=tuple(sorted({max(1,int(v)) for v in sizes})) or (max(1,int(default)),)
    smallest=values[0]
    manual=_nearest_not_above(values,default)
    if not dynamic or len(values)==1:
        return manual,manual,smallest,'fixed-unverified-controls'

    # Never jump more than ~2x the user's/default requested width even when the
    # browser exposes very large presets. CanvasGuard remains the hard ceiling.
    growth_cap=max(default,default*2)
    candidates=tuple(v for v in values if v<=growth_cap) or (manual,)
    classification=str(demand.get('classification') or 'balanced')
    if classification=='flat-shape':
        base=max(candidates)
        reason='auto-flat-shape'
    elif classification=='detail-heavy':
        target=max(smallest,int(round(default*.75)))
        base=_nearest_not_above(candidates,target)
        reason='auto-detail-heavy'
    else:
        base=_nearest_not_above(candidates,default)
        reason='auto-balanced'

    lower=[v for v in values if v<base]
    middle=max(lower) if lower else smallest
    return int(base),int(middle),int(smallest),reason


def assign_adaptive_brushes(execution_sequence: Sequence[dict], *, profile_key: str = '',
                            default_brush_px: int = 1,
                            browser_brush_plan: dict | None = None) -> dict:
    default=max(1,int(default_brush_px or 1))
    sizes,dynamic=verified_brush_sizes(profile_key,browser_brush_plan,default)
    demand=analyze_brush_demand(execution_sequence)
    base,middle,smallest,auto_reason=_select_auto_levels(sizes,default,demand,dynamic=dynamic)

    result=[];reasons=Counter();counts=Counter();previous=None;switches=0
    for raw in execution_sequence:
        entry=dict(raw);phase=str(entry.get('phase') or 'fine_detail').rsplit('/',1)[-1]
        protected=bool(entry.get('protected'))
        importance=max(0.0,min(1.0,_safe_float(entry.get('importance',0),0)))
        thin=_component_thin(entry)
        path=entry.get('path') or ();turns=max(0,len(path)-2)
        brush=base;reason=auto_reason

        if not dynamic:
            brush=base;reason='fixed-unverified-controls'
        elif phase.startswith('correction_'):
            brush=smallest;reason='accuracy-correction'
        elif phase=='cleanup' or protected:
            brush=smallest;reason='protected-detail'
        elif phase=='fine_detail':
            brush=smallest;reason='fine-detail'
        elif phase=='mid_detail':
            thin_value=thin if thin is not None else 999999
            if thin_value<=max(3,base*2) or importance>=.58 or turns>=2:
                brush=smallest;reason='edge-sensitive-mid-detail'
            else:
                brush=middle;reason='mid-detail'
        elif phase in ('structure','contour','outline') and (
            importance>=.46 or (thin is not None and thin<=max(5,base*2))
        ):
            brush=middle;reason='structure-detail-balance'
        else:
            brush=base;reason=auto_reason

        brush=int(max(1,brush));entry['brush_px']=brush;entry['brush_reason']=reason
        counts[brush]+=1;reasons[reason]+=1
        if previous is not None and brush!=previous:switches+=1
        previous=brush;result.append(entry)

    return {'execution_sequence':result,'metadata':{
        # Keep the historic engine name for compatibility with existing plan
        # diagnostics/tests; policy_version identifies the smarter selector.
        'engine':'Adaptive Brush Draw Motor v2','policy_version':3,
        'automatic_image_brush_selection':bool(dynamic),
        'dynamic_brush_enabled':bool(dynamic),
        'profile_key':str(profile_key or ''),
        'available_brush_sizes':tuple(map(int,sizes)),
        'requested_brush_px':default,'default_brush_px':base,
        'detail_brush_px':smallest,'mid_brush_px':middle,
        'auto_base_reason':auto_reason,'image_brush_demand':demand,
        'brush_path_counts':{str(k):int(v) for k,v in sorted(counts.items())},
        'brush_reason_counts':dict(reasons),'planned_brush_switches':int(switches),
        'geometry_changed':False,
        'quality_priority':'automatic image-aware base brush; protected/detail paths use the smallest verified brush'}}


def brush_for_entry(entry: dict, default_brush_px: int) -> int:
    try:return max(1,int(entry.get('brush_px',default_brush_px) or default_brush_px))
    except (TypeError,ValueError,AttributeError):return max(1,int(default_brush_px or 1))
