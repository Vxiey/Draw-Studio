"""Extra Fast 2.0 safe region selector.

Candidates have already passed Draw Studio's connected-component/closed-contour
safety checks.  This layer decides whether outline+Fill is actually cheaper than
keeping the same region as connected scanlines.  v2 reuses Region Fill Engine's
measured cost when available and charges Fill tool switching per colour batch,
not once per region.
"""
from collections import defaultdict
import math
from Precision import CanvasTransform,precision_path_count
from SpeedOptimizer import phase_delay,estimated_motion_seconds


def _legacy_cost(region, transform, options, cancelled=lambda:False):
    delay=float(options.get('delay',.01));speed=options.get('speed','Balanced')
    precision=options.get('precision','High');step=options.get('stroke_step_px',8)
    contour=list(region.get('contour') or ())
    moves=0
    for a,b in zip(contour,contour[1:]):
        if cancelled():raise InterruptedError()
        moves+=precision_path_count(transform.point(*a),transform.point(*b),precision,step)
    # Tool switches are deliberately excluded here. v2 adds them once per
    # colour batch below rather than once for every region.
    fill_cost=moves*max(.004,phase_delay(delay,speed,'path')) + .24
    spans=region.get('row_spans') or ()
    scan_moves=0
    for y,x0,x1 in spans:
        if cancelled():raise InterruptedError()
        scan_moves+=precision_path_count(transform.point(x0,y),transform.point(x1,y),precision,step)
    scan_cost=estimated_motion_seconds(scan_moves,len(spans),0,delay,speed)
    return scan_cost,fill_cost


def select_fast_regions(regions,source_size,target_size,options,cancelled=lambda:False):
    transform=CanvasTransform(*source_size,target_size)
    by_color=defaultdict(list);rejected=0
    for region in regions:
        if cancelled():raise InterruptedError()
        contour=list(region.get('contour') or ())
        if len(contour)<4 or contour[0]!=contour[-1]:
            rejected+=1;continue
        # Region Fill Engine v1.0.119+ already supplies cost/risk metadata. Use
        # it directly so Extra Fast does not pessimistically double-charge tool
        # switches and reject a region that is demonstrably faster to fill.
        try:
            scan_cost=float(region.get('stroke_cost_seconds'))
            fill_cost=float(region.get('fill_cost_seconds'))
        except (TypeError,ValueError,OverflowError):
            scan_cost,fill_cost=_legacy_cost(region,transform,options,cancelled)
        if not math.isfinite(scan_cost) or not math.isfinite(fill_cost) or scan_cost<=0 or fill_cost<=0 or fill_cost>=scan_cost*.94:
            rejected+=1;continue
        item=dict(region)
        item['extra_fast_strategy']='OUTLINE_FILL'
        item['extra_fast_scanline_cost_seconds']=round(scan_cost,5)
        item['extra_fast_fill_cost_seconds']=round(fill_cost,5)
        item['extra_fast_region_saving_seconds']=round(max(0.,scan_cost-fill_cost),5)
        try:key=int(item.get('color_index',-1))
        except (TypeError,ValueError):key=-1
        by_color[key].append(item)

    # Shared Fill/restore controls are paid once for a same-colour batch.
    ui_actions=len(options.get('fill_tool_actions') or ())+len(options.get('fill_restore_actions') or ())
    if ui_actions==0 and options.get('fill_tool_available'):ui_actions=2
    try:
        ui_delay=float(options.get('ui_control_delay',.22))
    except (TypeError,ValueError,OverflowError):
        ui_delay=.22
    if not math.isfinite(ui_delay) or ui_delay<0:
        ui_delay=.22
    batch_overhead=max(0.,ui_actions*ui_delay)
    accepted=[];seconds=0.;saved=0.;batch_rejected=0
    for color,items in sorted(by_color.items(),key=lambda kv:kv[0]):
        if cancelled():raise InterruptedError()
        batch_scan=sum(float(r['extra_fast_scanline_cost_seconds']) for r in items)
        batch_fill=sum(float(r['extra_fast_fill_cost_seconds']) for r in items)+batch_overhead
        if batch_fill>=batch_scan*.96:
            rejected+=len(items);batch_rejected+=len(items);continue
        accepted.extend(items);seconds+=batch_fill;saved+=batch_scan-batch_fill

    pixels=sum(max(0,int(r.get('area_pixels',0) or 0)) for r in accepted)
    return accepted,{
        'engine':'Extra Fast 2.0 outline/fill selector',
        'accepted_regions':len(accepted),'cost_rejected_regions':rejected,
        'batch_rejected_regions':batch_rejected,'fill_color_batches':len({int(r.get('color_index',-1)) for r in accepted}),
        'fill_pixels':pixels,'fill_estimated_seconds':round(seconds,3),
        'estimated_seconds_saved_vs_scanlines':round(saved,3),
        'fallback_strategy':'connected serpentine scanlines',
        'tool_switch_cost_model':'shared per color batch',
    }
