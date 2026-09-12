from pathlib import Path

p=Path('AdaptiveRegionHybrid.py')
text=p.read_text(encoding='utf-8')

if 'import math\n' not in text:
    text=text.replace('import time\n','import time\nimport math\n',1)


def replace_block(source,start_marker,end_marker,replacement):
    start=source.index(start_marker)
    end=source.index(end_marker,start)
    return source[:start]+replacement+source[end:]

brush_block=r'''def _candidate_paths_for_brush(target:np.ndarray,residual:np.ndarray,brush_px:int,*,
                               model,comp,phase:str,final_size:bool,origin=(0,0),cancelled=lambda:False):
    """Choose a safe, cost-efficient run layout inside one component ROI.

    Extra Fast tests the native brush stride and one denser half-stride for wide
    brushes.  Candidates within 90% of the best unique-pixel gain compete on
    calibrated execution seconds per newly covered pixel instead of raw gain
    alone.  This avoids accepting a much slower layout for a negligible coverage
    increase while keeping every simulated brush footprint inside the component.
    """
    _cancel(cancelled)
    brush=max(1,int(brush_px))
    safe=_eroded_centers(target,brush)
    useful=safe & _centers_touching_mask(residual,brush)
    if not np.any(useful):return [],np.zeros_like(target,dtype=np.bool_),0.0
    if final_size:
        strides=(1,)
    else:
        strides=tuple(dict.fromkeys((brush,max(1,brush//2))))
    candidates=[]
    for stride in strides:
        offsets=(0,) if stride==1 else tuple(range(stride))
        for orientation in ("horizontal","vertical"):
            for offset in offsets:
                _cancel(cancelled)
                local_paths=_runs_from_mask(useful,row_stride=stride,row_offset=offset,orientation=orientation)
                if not local_paths:continue
                trial=np.zeros_like(target,dtype=np.bool_)
                for path in local_paths:_paint_path(trial,path,brush)
                if np.any(trial & ~target):continue
                gained=int(np.count_nonzero(trial & residual))
                if gained<=0:continue
                paths=_offset_paths(local_paths,origin)
                seq=_entry_sequence(comp.color_index,paths,phase=phase,comp=comp,brush_px=brush,
                                    method=f"region-brush-pack-{brush}px")
                cost=max(.000001,float(model.sequence_cost(
                    seq,initial_color=int(comp.color_index),initial_brush=brush).total_seconds))
                candidates.append((gained,cost,len(paths),stride,orientation,offset,paths,trial))
    if not candidates:return [],np.zeros_like(target,dtype=np.bool_),0.0
    max_gain=max(row[0] for row in candidates)
    gain_floor=max(1,int(max_gain*.90))
    eligible=[row for row in candidates if row[0]>=gain_floor]
    best=min(eligible,key=lambda row:(row[1]/max(1,row[0]),row[1],row[2],-row[0],row[3],row[4],row[5]))
    return list(best[6]),best[7],float(best[1])


def _brush_pack_candidate(comp,component_map,options,model,cancelled=lambda:False):
    """Find the cheapest exact verified multi-brush packing for one region.

    Work is bbox-local. Brush sizes that physically cannot fit the component ROI
    are rejected before erosion. A bounded set of verified brush ladders is then
    evaluated so an expensive intermediate brush switch is never mandatory just
    because the target exposes five controls.
    """
    default=max(1,int(options.get("brush_px") or 1))
    verified,dynamic=verified_brush_sizes(str(options.get("profile_key") or ""),
                                          options.get("browser_brush_plan"),default)
    verified=tuple(sorted({max(1,int(v)) for v in verified},reverse=True))
    if not dynamic or len(verified)<2:
        return None,"no verified multi-brush controls"
    smallest=min(verified)
    if comp.area<max(48,smallest*smallest*6):
        return None,"component too small for region brush packing"

    h,w=component_map.shape
    x0,y0,x1,y1=map(int,comp.bbox)
    x0=max(0,min(w-1,x0));x1=max(0,min(w-1,x1))
    y0=max(0,min(h-1,y0));y1=max(0,min(h-1,y1))
    if x1<x0 or y1<y0:return None,"invalid component bbox"
    roi_map=component_map[y0:y1+1,x0:x1+1]
    target=roi_map==comp.component_id
    if not np.any(target):return None,"empty component"

    roi_h,roi_w=target.shape
    fit_limit=max(1,min(roi_w,roi_h))
    sizes=tuple(v for v in verified if v<=fit_limit)
    pruned=tuple(v for v in verified if v>fit_limit)
    if smallest not in sizes or len(sizes)<2:
        return None,f"fewer than two verified brushes fit ROI {roi_w}x{roi_h}; pruned={pruned}"

    ladders=[]
    def add_ladder(raw):
        values=tuple(sorted({int(v) for v in raw if int(v) in sizes},reverse=True))
        if smallest not in values:values=tuple(sorted(set(values+(smallest,)),reverse=True))
        if len(values)>=2 and values not in ladders:ladders.append(values)
    add_ladder(sizes)
    add_ladder((sizes[0],smallest))
    add_ladder(tuple(sizes[::2])+(smallest,))
    if len(sizes)>3:add_ladder(tuple(sizes[1::2])+(sizes[0],smallest))
    for drop in sizes[1:-1]:
        add_ladder(tuple(v for v in sizes if v!=drop))
    ladders=ladders[:6]

    total_drawable=int(np.count_nonzero(component_map>=0))
    base_phase=_phase(comp,total_drawable)
    exact_candidates=[]
    for ladder in ladders:
        _cancel(cancelled)
        painted=np.zeros_like(target,dtype=np.bool_)
        sequence=[];flat_paths=[];used=[];per_size=[]
        for brush in ladder:
            _cancel(cancelled)
            residual=target & ~painted
            if not np.any(residual):break
            paths,trial,local_cost=_candidate_paths_for_brush(
                target,residual,brush,model=model,comp=comp,
                phase=("detail" if brush==smallest else base_phase),
                final_size=(brush==smallest),origin=(x0,y0),cancelled=cancelled)
            if not paths:continue
            newly=int(np.count_nonzero(trial & residual))
            if newly<=0:continue
            painted |= trial
            used.append(brush);flat_paths.extend(paths)
            sequence.extend(_entry_sequence(
                comp.color_index,paths,phase=("detail" if brush==smallest else base_phase),
                comp=comp,brush_px=brush,method=f"region-brush-pack-{brush}px"))
            per_size.append({"brush_px":brush,"paths":len(paths),"new_pixels":newly,
                             "local_cost_seconds":round(local_cost,6)})
        if np.any(painted & ~target):continue
        missing=int(np.count_nonzero(target & ~painted))
        if missing or not np.array_equal(painted,target):continue
        if len(set(used))<2:continue
        cost=model.sequence_cost(
            sequence,initial_color=int(comp.color_index),initial_brush=default).total_seconds
        exact_candidates.append({"sequence":sequence,"paths":flat_paths,"cost":float(cost),
            "brush_px":max(used),"method":"region-brush-pack","exact":True,
            "used_brush_sizes":tuple(used),"packing":per_size,
            "requested_ladder":tuple(ladder),"covered_pixels":int(np.count_nonzero(painted))})

    if not exact_candidates:
        return None,f"verified brush ladders could not exactly cover ROI; eligible={sizes} pruned={pruned}"
    best=min(exact_candidates,key=lambda row:(row["cost"],len(row["sequence"]),-len(set(row["used_brush_sizes"]))))
    roi_pixels=int(target.size);canvas_pixels=int(component_map.size)
    reduction=max(0.0,1.0-(roi_pixels/max(1,canvas_pixels)))
    best.update({
        "packing_roi_bbox":(x0,y0,x1,y1),"packing_workspace_pixels":roi_pixels,
        "packing_canvas_pixels":canvas_pixels,
        "packing_workspace_reduction_percent":round(reduction*100.0,4),
        "verified_brush_sizes":verified,"eligible_brush_sizes":sizes,"pruned_brush_sizes":pruned,
        "ladder_candidates_evaluated":len(ladders),"exact_ladder_candidates":len(exact_candidates),
    })
    return best,(
        f"exact verified brush packing chose ladder {best['requested_ladder']} using {best['used_brush_sizes']} "
        f"from {len(exact_candidates)}/{len(ladders)} exact candidates; pruned={pruned}")


'''
text=replace_block(text,'def _candidate_paths_for_brush(','def _choose_component(',brush_block)

budget_schedule=r'''def _budget_seconds(options,model,choices,fill_regions,image_size,fitted):
    """Resolve one canonical render budget, then subtract real non-path work.

    TimeBudgetEngine owns timer/reserve semantics. If a profile/tuner already
    supplied resolved deadline fields they win. This prevents Extra Fast from
    inventing a second reserve on top of the UI/game preset reserve.
    """
    mode=str(options.get("time_budget_mode") or "")
    active=bool(options.get("time_budget_active")) and mode not in ("Unlimited","Unlimited / Accuracy","Off")
    try:manual=float(options.get("manual_max_seconds") or options.get("max_seconds") or 180)
    except Exception:manual=180.0
    total=manual;reserve=0.0;render_budget=float('inf');deadline_source="inactive"
    if active:
        def finite(raw,default=0.0):
            try:value=float(raw)
            except Exception:return float(default)
            return value if math.isfinite(value) else float(default)
        resolved_render=finite(options.get("deadline_render_budget_seconds"),0.0)
        resolved_total=finite(options.get("deadline_total_seconds"),0.0)
        resolved_reserve=finite(options.get("deadline_safety_reserve_seconds"),-1.0)
        if resolved_render>0:
            render_budget=resolved_render
            total=resolved_total if resolved_total>0 else resolved_render+max(0.0,resolved_reserve)
            reserve=max(0.0,total-render_budget) if resolved_reserve<0 else max(0.0,resolved_reserve)
            deadline_source="pre-resolved deadline fields"
        else:
            try:
                from TimeBudgetEngine import resolve_budget
                resolved=resolve_budget(mode,manual,options.get("deadline_safety_reserve","Auto"))
            except Exception:
                resolved={"active":False}
            if resolved.get("active"):
                total=float(resolved.get("total_seconds") or manual)
                reserve=max(0.0,float(resolved.get("reserve_seconds") or 0.0))
                render_budget=max(0.0,float(resolved.get("render_budget_seconds") or (total-reserve)))
                deadline_source=str(resolved.get("source") or "TimeBudgetEngine")
            else:
                total=max(5.0,manual)
                reserve=max(0.0,finite(options.get("deadline_safety_reserve_seconds"),0.0))
                render_budget=max(0.0,total-reserve)
                deadline_source="legacy active deadline fields"

    colors=len({c.color_index for c in choices})
    fixed=model.fixed_overhead(active_colors=0,fill_actions=0)
    fill_meta={"fill_regions":0,"fill_color_batches":0,"total_seconds":0.0}
    if fill_regions:
        try:
            from RegionFillEngine import estimate_fill_execution_seconds
            fill_meta=dict(estimate_fill_execution_seconds(fill_regions,image_size,fitted,options) or fill_meta)
        except Exception:
            fill_meta={"fill_regions":len(fill_regions),"fill_color_batches":0,
                       "total_seconds":len(fill_regions)*model.switch_cost("fill"),"fallback":True}
    fill_seconds=max(0.0,float(fill_meta.get("total_seconds",0.0) or 0.0))
    fill_colors={int(r.get("color_index",-1)) for r in (fill_regions or ())
                 if isinstance(r,dict) and int(r.get("color_index",-1))>=0}
    fill_palette_seconds=(0.0 if options.get("paint_current_color") else
                          len(fill_colors)*model.switch_cost("palette_change"))
    verification_seconds=(colors*model.switch_cost("verification")
                          if options.get("adaptive_color_verification") else 0.0)
    clear_seconds=max(0.0,float(options.get("canvas_clear_estimate_seconds",0.0) or 0.0))
    outside_seconds=(fixed.total_seconds+fill_seconds+fill_palette_seconds+
                     verification_seconds+clear_seconds)
    usable=max(0.0,render_budget-outside_seconds) if active else float('inf')
    return active,usable,{
        "base_fixed":fixed.as_dict(),"fill":fill_meta,
        "fill_palette_seconds":round(fill_palette_seconds,6),
        "adaptive_verification_seconds":round(verification_seconds,6),
        "canvas_clear_seconds":round(clear_seconds,6),
        "outside_sequence_seconds":round(outside_seconds,6),
        "deadline":{"source":deadline_source,"total_seconds":round(total,6),
                    "reserve_seconds":round(reserve,6),
                    "render_budget_seconds":None if not active else round(render_budget,6)},
    },reserve,total


def _schedule(choices, sequences_by_component, size, model,options,fill_regions,*,fitted=None):
    budget_fitted=tuple(fitted) if fitted is not None else tuple(size)
    active,usable,fixed_meta,reserve,limit=_budget_seconds(
        options,model,choices,fill_regions,size,budget_fitted)
    weights={"foundation":1.25,"structure":1.18,"detail":1.04,"correction":.78}
    phase_order={p:i for i,p in enumerate(PHASES)}
    by_id={c.component_id:c for c in choices}
    try:initial_brush=max(1,int(options.get("brush_px") or 1))
    except Exception:initial_brush=1

    geom_cache={}
    def geometry(c):
        cached=geom_cache.get(c.component_id)
        if cached is not None:return cached
        seq=sequences_by_component.get(c.component_id) or ()
        rows=[e for e in seq if e.get("path")]
        if not rows:
            value=(None,None,initial_brush,initial_brush)
        else:
            value=(tuple(map(int,rows[0]["path"][0])),tuple(map(int,rows[-1]["path"][-1])),
                   max(1,int(rows[0].get("brush_px") or initial_brush)),
                   max(1,int(rows[-1].get("brush_px") or initial_brush)))
        geom_cache[c.component_id]=value;return value

    def transition_seconds(c,cursor,current_color,current_brush):
        start,_end,first_brush,_last_brush=geometry(c)
        travel=0.0
        if cursor is not None and start is not None:
            px=math.hypot((start[0]-cursor[0])*float(getattr(model,"scale_x",1.0)),
                          (start[1]-cursor[1])*float(getattr(model,"scale_y",1.0)))
            travel=min(.10,px*.000045)*float(getattr(model,"multiplier",1.0) or 1.0)
        palette=0.0
        if (not options.get("paint_current_color") and
            (current_color is None or int(current_color)!=int(c.color_index))):
            palette=float(model.switch_cost("palette_change"))
        brush=0.0 if current_brush is None or int(current_brush)==int(first_brush) else float(model.switch_cost("brush_change"))
        return travel+palette+brush

    ordering_stats={"greedy_batches":0,"serpentine_batches":0,"components_ordered":0}
    def order_rows(ids):
        selected_rows=[by_id[i] for i in ids if i in by_id]
        cursor=None;current_color=None;current_brush=initial_brush;ordered=[]
        for phase in PHASES:
            phase_rows=[c for c in selected_rows if c.phase==phase]
            colors={int(c.color_index) for c in phase_rows}
            while colors:
                if current_color in colors:
                    ci=int(current_color)
                else:
                    def color_key(color):
                        rows=[c for c in phase_rows if int(c.color_index)==color]
                        best=min((transition_seconds(c,cursor,current_color,current_brush) for c in rows),default=0.0)
                        gain=max((c.gain_per_ms for c in rows),default=0.0)
                        return (best,-gain,color)
                    ci=min(colors,key=color_key)
                batch=[c for c in phase_rows if int(c.color_index)==ci]
                if len(batch)<=96:
                    ordering_stats["greedy_batches"]+=1
                    remaining=list(batch)
                    while remaining:
                        pick=min(remaining,key=lambda c:(transition_seconds(c,cursor,current_color,current_brush),
                                                         -c.gain_per_ms,-c.visual_gain,c.component_id))
                        remaining.remove(pick);ordered.append(pick)
                        _start,cursor,_first,current_brush=geometry(pick)
                        current_color=pick.color_index
                else:
                    ordering_stats["serpentine_batches"]+=1
                    band_h=max(1,int(math.ceil(max(1,size[1])/16.0)))
                    def snake_key(c):
                        start,_end,first_brush,_last=geometry(c)
                        x,y=start or (0,0);band=max(0,int(y//band_h))
                        x_key=x if band%2==0 else -x
                        brush_penalty=0 if int(first_brush)==int(current_brush or first_brush) else 1
                        return (band,x_key,brush_penalty,-c.gain_per_ms,c.component_id)
                    for pick in sorted(batch,key=snake_key):
                        ordered.append(pick);_start,cursor,_first,current_brush=geometry(pick);current_color=pick.color_index
                colors.remove(ci)
        ordering_stats["components_ordered"]+=len(ordered)
        return ordered

    def build_sequence(ids):
        sequence=[];serial=0
        for c in order_rows(ids):
            for raw in sequences_by_component[c.component_id]:
                e=dict(raw);e["serial"]=serial;serial+=1;sequence.append(e)
        return sequence

    def exact_cost(sequence):
        raw=model.sequence_cost(sequence,initial_brush=initial_brush)
        risk=(model.risk_adjusted_seconds(raw.total_seconds)
              if active and hasattr(model,"risk_adjusted_seconds") else raw.total_seconds)
        return raw,float(risk)

    hard_seed_ids=set();soft_seed_ids=set();phase_seed_ids=set();spatial_seed_ids=set()
    if not active:
        selected={c.component_id for c in choices}
    else:
        selected=set();used=0.0
        protected=[c for c in choices if c.protected_pixels]
        protected.sort(key=lambda c:(-c.importance,-c.visual_gain,c.estimated_seconds,c.component_id))
        protected_cap=max(0.0,usable*.18);protected_used=0.0
        for c in protected[:8]:
            if used+c.estimated_seconds>usable:continue
            if protected_used+c.estimated_seconds>protected_cap and hard_seed_ids:continue
            selected.add(c.component_id);hard_seed_ids.add(c.component_id)
            used+=c.estimated_seconds;protected_used+=c.estimated_seconds

        for phase in ("foundation","structure","detail"):
            rows=[c for c in choices if c.phase==phase and c.component_id not in selected]
            if not rows:continue
            best=max(rows,key=lambda c:(c.gain_per_ms*weights[c.phase],c.visual_gain,-c.estimated_seconds,-c.component_id))
            if used+best.estimated_seconds<=usable:
                selected.add(best.component_id);soft_seed_ids.add(best.component_id);phase_seed_ids.add(best.component_id)
                used+=best.estimated_seconds

        cell_best={}
        for c in choices:
            if c.component_id in selected:continue
            seq=sequences_by_component[c.component_id]
            pts=[p for e in seq for p in (e.get("path") or ())[:1]]
            if not pts:continue
            x,y=pts[0];cx=min(3,max(0,int(x/max(1,size[0])*4)));cy=min(3,max(0,int(y/max(1,size[1])*4)))
            old=cell_best.get((cx,cy))
            if old is None or (c.visual_gain,c.area,-c.component_id)>(old.visual_gain,old.area,-old.component_id):
                cell_best[(cx,cy)]=c
        for c in sorted(cell_best.values(),key=lambda c:(-c.visual_gain,c.component_id)):
            if used+c.estimated_seconds<=usable:
                selected.add(c.component_id);soft_seed_ids.add(c.component_id);spatial_seed_ids.add(c.component_id)
                used+=c.estimated_seconds
        rest=[c for c in choices if c.component_id not in selected]
        rest.sort(key=lambda c:(-(c.gain_per_ms*weights[c.phase]),-c.visual_gain,c.component_id))
        for c in rest:
            if used+c.estimated_seconds<=usable:
                selected.add(c.component_id);used+=c.estimated_seconds

    sequence=build_sequence(selected)
    seq_cost,risk_cost=exact_cost(sequence)
    trimmed=[];refilled=[];swapped=[]

    if active:
        important_protected={c.component_id for c in choices
                             if c.component_id in selected and c.protected_pixels and c.importance>=.50}
        hard_protected=hard_seed_ids|important_protected
        while selected and risk_cost>usable+1e-9:
            rows=order_rows(selected)
            removable=[c for c in rows if c.component_id not in hard_protected and c.component_id not in soft_seed_ids]
            if not removable:removable=[c for c in rows if c.component_id not in hard_protected]
            if not removable:removable=rows
            victim=min(removable,key=lambda c:(c.gain_per_ms*weights[c.phase],c.visual_gain,-c.estimated_seconds,c.component_id))
            selected.remove(victim.component_id);trimmed.append(victim.component_id)
            sequence=build_sequence(selected);seq_cost,risk_cost=exact_cost(sequence)

        omitted=[c for c in choices if c.component_id not in selected]
        omitted.sort(key=lambda c:(-(c.gain_per_ms*weights[c.phase]),-c.visual_gain,c.component_id))
        for c in omitted[:64]:
            trial=set(selected);trial.add(c.component_id)
            trial_sequence=build_sequence(trial);trial_cost,trial_risk=exact_cost(trial_sequence)
            if trial_risk<=usable+1e-9:
                selected=trial;sequence=trial_sequence;seq_cost=trial_cost;risk_cost=trial_risk;refilled.append(c.component_id)

        for _ in range(8):
            omitted=[c for c in choices if c.component_id not in selected]
            omitted.sort(key=lambda c:(-c.visual_gain,-c.gain_per_ms,c.component_id))
            victims=[c for c in choices if c.component_id in selected and c.component_id not in hard_protected]
            victims.sort(key=lambda c:(c.visual_gain,c.gain_per_ms,-c.estimated_seconds,c.component_id))
            best_swap=None
            for incoming in omitted[:16]:
                for victim in victims[:16]:
                    gain_delta=incoming.visual_gain-victim.visual_gain
                    if gain_delta<=1e-12:continue
                    trial=set(selected);trial.remove(victim.component_id);trial.add(incoming.component_id)
                    trial_sequence=build_sequence(trial);trial_cost,trial_risk=exact_cost(trial_sequence)
                    if trial_risk>usable+1e-9:continue
                    score=(gain_delta,-trial_risk,-incoming.estimated_seconds,-incoming.component_id,victim.component_id)
                    if best_swap is None or score>best_swap[0]:
                        best_swap=(score,trial,trial_sequence,trial_cost,trial_risk,incoming.component_id,victim.component_id)
            if best_swap is None:break
            _score,selected,sequence,seq_cost,risk_cost,incoming_id,victim_id=best_swap
            swapped.append((victim_id,incoming_id))

    groups=[[] for _ in range(max([c.color_index for c in choices],default=-1)+1)]
    for e in sequence:
        while len(groups)<=int(e["color_index"]):groups.append([])
        groups[int(e["color_index"])].append(tuple(e["path"]))
    utilization=(risk_cost/usable*100.0) if active and usable>0 else 0.0
    nominal_utilization=(seq_cost.total_seconds/usable*100.0) if active and usable>0 else 0.0
    return groups,sequence,{
        "deadline_active":active,"deadline_seconds":round(limit,4),"usable_path_seconds":round(usable,4),
        "fixed_overhead":fixed_meta,"safety_reserve_seconds":round(reserve,4),
        "selected_components":len(selected),"total_components":len(choices),
        "dropped_components":len(choices)-len(selected),
        "selected_path_cost_seconds":round(seq_cost.total_seconds,6),
        "risk_adjusted_path_cost_seconds":round(risk_cost,6),
        "calibration_uncertainty_multiplier":round(float(getattr(model,"uncertainty_multiplier",1.0) or 1.0),6),
        "selected_operation_cost":seq_cost.as_dict(),
        "exact_budget_guard":True,"risk_adjusted_budget_guard":True,
        "budget_trimmed_components":len(trimmed),"budget_refilled_components":len(refilled),
        "budget_swapped_components":len(swapped),"budget_swap_pairs":[list(v) for v in swapped[:16]],
        "budget_utilization_percent":round(utilization,3),"nominal_budget_utilization_percent":round(nominal_utilization,3),
        "palette_switches":int(seq_cost.palette_switches),"brush_switches":int(seq_cost.brush_switches),
        "protected_seed_components":len(hard_seed_ids),"phase_seed_components":len(phase_seed_ids),
        "spatial_seed_components":len(spatial_seed_ids),
        "phase_color_batching":True,"transition_cost_ordering":True,"brush_aware_ordering":True,
        "ordering_stats":dict(ordering_stats),
    }

'''
text=replace_block(text,'def _budget_seconds(','def simulate_quantized_plan',budget_schedule)

fill_helpers=r'''def _fill_seed(region):
    raw=region.get("seed_pixel") if isinstance(region,dict) else None
    try:return tuple(map(int,raw))
    except Exception:pass
    try:
        x0,y0,x1,y1=map(int,region.get("bbox"))
        return ((x0+x1)//2,(y0+y1)//2)
    except Exception:return (0,0)


def _order_fill_regions_for_execution(regions):
    """Color-batch Fill regions and draw the largest safe region first.

    The ordered list is subsequently passed through StatefulFillSimulation, so
    the exact order used for execution is safety-validated rather than merely
    being a cosmetic sort.
    """
    rows=[dict(r) for r in (regions or ()) if isinstance(r,dict)]
    by_color={}
    for r in rows:by_color.setdefault(int(r.get("color_index",-1)),[]).append(r)
    color_order=sorted(by_color,key=lambda ci:(-sum(max(0,int(r.get("area_pixels",0) or 0)) for r in by_color[ci]),ci))
    out=[];batches=[]
    for ci in color_order:
        remaining=list(by_color[ci])
        if not remaining:continue
        first=max(remaining,key=lambda r:(int(r.get("area_pixels",0) or 0),-_fill_seed(r)[1],-_fill_seed(r)[0]))
        remaining.remove(first);batch=[first];cursor=_fill_seed(first)
        while remaining:
            pick=min(remaining,key=lambda r:(((_fill_seed(r)[0]-cursor[0])**2+(_fill_seed(r)[1]-cursor[1])**2),
                                             -int(r.get("area_pixels",0) or 0),_fill_seed(r)[1],_fill_seed(r)[0]))
            remaining.remove(pick);batch.append(pick);cursor=_fill_seed(pick)
        out.extend(batch);batches.append({"color_index":ci,"regions":len(batch),
                                          "pixels":sum(max(0,int(r.get("area_pixels",0) or 0)) for r in batch)})
    return out,{"policy":"color-batched-large-first-nearest","color_batches":len(batches),"batches":batches}


'''
marker='def _build_fill_regions(groups,palette_rgb,image_size,fitted,options,cancelled):'
idx=text.index(marker)
text=text[:idx]+fill_helpers+text[idx:]

old='''        accepted,mask_meta=filter_fill_regions_by_source_mask(accepted,image_size,margin_px=margin)\n        accepted,state_meta=filter_stateful_fill_regions(accepted,image_size,brush_px=max(1,int(options.get("brush_px") or 1)),cancelled=cancelled)\n        meta=dict(meta);meta["safe_fill_mask"]=mask_meta;meta["stateful_fill_simulation"]=state_meta\n        meta["fill_safe_regions"]=len(accepted);meta["fill_actions"]=len(accepted)'''
new='''        accepted,mask_meta=filter_fill_regions_by_source_mask(accepted,image_size,margin_px=margin)\n        accepted,fill_order_meta=_order_fill_regions_for_execution(accepted)\n        accepted,state_meta=filter_stateful_fill_regions(accepted,image_size,brush_px=max(1,int(options.get("brush_px") or 1)),cancelled=cancelled)\n        meta=dict(meta);meta["safe_fill_mask"]=mask_meta;meta["stateful_fill_simulation"]=state_meta\n        meta["fill_execution_order"]=fill_order_meta\n        meta["fill_safe_regions"]=len(accepted);meta["fill_actions"]=len(accepted)'''
if text.count(old)!=1:raise SystemExit(f'fill ordering anchor count={text.count(old)}')
text=text.replace(old,new,1)

old='''            "extra_fast_regional_route":bool(options.get("extra_fast")),'''
new='''            "extra_fast_regional_route":bool(options.get("extra_fast")),\n            "extra_fast_10_pack":True,\n            "extra_fast_10_improvements":(\n                "canonical-deadline-reserve","risk-adjusted-budget-guard","protected-detail-reserve",\n                "phase-minimum-seeding","travel-aware-ordering","brush-aware-ordering",\n                "exact-quality-swap","brush-roi-pruning","adaptive-brush-stride","cost-aware-brush-ladders",\n            ),'''
if text.count(old)!=1:raise SystemExit(f'metadata anchor count={text.count(old)}')
text=text.replace(old,new,1)

p.write_text(text,encoding='utf-8')

Path('test_extra_fast_10_improvements_rc25.py').write_text(r'''import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

import AdaptiveRegionHybrid as ar
from AdaptiveRegionHybrid import RegionChoice
from ExecutionCostModel import build_cost_model
from TimeBudgetEngine import automatic_reserve
from Version import APP_VERSION


def opts(limit=60.0):
    return {'profile_key':'gartic','brush_px':2,'speed':'Balanced','delay':0.0,
            'time_budget_active':True,'time_budget_mode':'Custom','max_seconds':limit,
            'manual_max_seconds':limit,'deadline_safety_reserve':'Auto','paint_current_color':False,
            'adaptive_color_verification':False,'fill_tool_available':False,
            'browser_brush_plan':{'target_position':(10,10),'confidence':.99,
                'nominal_sizes':[2,4,8,16,28],'verified_sizes':[2,4,8,16,28],
                'control_positions':[(1,1),(2,1),(3,1),(4,1),(5,1)],'safe_guard_px':4}}


def choice(cid,color,phase='structure',cost=.2,gain=.1,brush=2,protected=0,importance=.3):
    return RegionChoice(cid,color,'test',phase,100,importance,.2,protected,cost,gain,
                        gain/max(.001,cost*1000),1,brush,True,'test')


def entry(cid,color,x,brush=2,fake_cost=None,phase='structure'):
    row={'component_id':cid,'color_index':color,'brush_px':brush,'path':((x,10),(x+5,10)),'phase':phase}
    if fake_cost is not None:row['fake_cost']=float(fake_cost)
    return [row]


class FakeBreakdown:
    def __init__(self,total):
        self.total_seconds=float(total);self.palette_switches=0;self.brush_switches=0
        self.tool_switches=0;self.palette_seconds=0.0;self.brush_seconds=0.0
    def as_dict(self):return {'total_seconds':self.total_seconds,'palette_switches':0,'brush_switches':0}


class FakeModel:
    scale_x=1.0;scale_y=1.0;multiplier=1.0;uncertainty_multiplier=1.0
    def switch_cost(self,kind):return {'palette_change':.1,'brush_change':.2,'verification':.1,'fill':.1}.get(kind,.1)
    def fixed_overhead(self,**kwargs):return FakeBreakdown(0.0)
    def risk_adjusted_seconds(self,value):return float(value)
    def sequence_cost(self,sequence,**kwargs):
        return FakeBreakdown(sum(float(e.get('fake_cost',.1)) for e in sequence))


class ExtraFastTenImprovementTests(unittest.TestCase):
    def test_canonical_deadline_reserve_is_used_once(self):
        o=opts(60);m=build_cost_model(o,(200,100),(200,100))
        active,usable,meta,reserve,total=ar._budget_seconds(o,m,[],[],(200,100),(200,100))
        self.assertTrue(active);self.assertEqual(total,60.0)
        self.assertAlmostEqual(reserve,automatic_reserve(60.0),places=6)
        self.assertAlmostEqual(meta['deadline']['render_budget_seconds'],60.0-reserve,places=6)
        self.assertLess(usable,meta['deadline']['render_budget_seconds'])

    def test_fill_order_batches_colors_large_first(self):
        rows=[{'color_index':1,'area_pixels':20,'seed_pixel':(50,50)},
              {'color_index':0,'area_pixels':10,'seed_pixel':(5,5)},
              {'color_index':1,'area_pixels':100,'seed_pixel':(20,20)},
              {'color_index':0,'area_pixels':80,'seed_pixel':(8,8)}]
        ordered,meta=ar._order_fill_regions_for_execution(rows)
        colors=[r['color_index'] for r in ordered]
        self.assertEqual(len(meta['batches']),2)
        self.assertLessEqual(sum(a!=b for a,b in zip(colors,colors[1:])),1)
        for color in set(colors):
            batch=[r for r in ordered if r['color_index']==color]
            self.assertEqual(batch[0]['area_pixels'],max(r['area_pixels'] for r in batch))

    def test_schedule_reserves_protected_and_phase_components(self):
        o=opts(30);m=build_cost_model(o,(200,120),(200,120))
        cs=[choice(1,0,'foundation',.1,.4),choice(2,0,'structure',.1,.3),
            choice(3,1,'detail',.1,.2,protected=8,importance=.9),choice(4,1,'correction',.1,.1)]
        seqs={c.component_id:entry(c.component_id,c.color_index,c.component_id*20,c.brush_px,phase=c.phase) for c in cs}
        _g,_s,meta=ar._schedule(cs,seqs,(200,120),m,o,[])
        self.assertGreaterEqual(meta['protected_seed_components'],1)
        self.assertGreaterEqual(meta['phase_seed_components'],2)
        self.assertTrue(meta['risk_adjusted_budget_guard'])
        self.assertGreaterEqual(meta['risk_adjusted_path_cost_seconds'],meta['selected_path_cost_seconds'])

    def test_transition_ordering_prefers_near_component(self):
        o=opts(30);m=build_cost_model(o,(400,100),(400,100))
        cs=[choice(1,0,gain=.9),choice(2,0,gain=.2),choice(3,0,gain=.19)]
        seqs={1:entry(1,0,0),2:entry(2,0,300),3:entry(3,0,20)}
        _g,s,meta=ar._schedule(cs,seqs,(400,100),m,o,[])
        ids=[]
        for e in s:
            if e['component_id'] not in ids:ids.append(e['component_id'])
        self.assertEqual(ids[:3],[1,3,2])
        self.assertTrue(meta['transition_cost_ordering'])

    def test_transition_ordering_accounts_for_brush_switch(self):
        o=opts(30);m=build_cost_model(o,(150,100),(150,100))
        cs=[choice(1,0,gain=.9,brush=2),choice(2,0,gain=.2,brush=28),choice(3,0,gain=.19,brush=2)]
        seqs={1:entry(1,0,0,2),2:entry(2,0,10,28),3:entry(3,0,18,2)}
        _g,s,meta=ar._schedule(cs,seqs,(150,100),m,o,[])
        ids=[]
        for e in s:
            if e['component_id'] not in ids:ids.append(e['component_id'])
        self.assertEqual(ids[:3],[1,3,2]);self.assertTrue(meta['brush_aware_ordering'])

    def test_wide_brush_searches_native_and_half_stride(self):
        target=np.ones((24,40),dtype=np.bool_);residual=target.copy();seen=[]
        comp=SimpleNamespace(component_id=1,color_index=0,area=int(target.size),bbox=(0,0,39,23),
            width=40,height=24,importance_mean=.1,importance_max=.1,edge_mean=.1,contour_mean=.1,
            protected_pixels=0,protected_ratio=0.0)
        m=build_cost_model(opts(30),(40,24),(40,24));real=ar._runs_from_mask
        def spy(mask,row_stride=1,row_offset=0,orientation='horizontal'):
            seen.append(int(row_stride));return real(mask,row_stride,row_offset,orientation)
        with patch.object(ar,'_runs_from_mask',side_effect=spy):
            paths,painted,_cost=ar._candidate_paths_for_brush(target,residual,8,model=m,comp=comp,phase='foundation',final_size=False)
        self.assertTrue(paths);self.assertTrue(np.any(painted));self.assertIn(8,seen);self.assertIn(4,seen)

    def test_brush_pack_prunes_oversized_controls_and_tests_ladders(self):
        cmap=np.full((12,12),7,dtype=np.int32)
        runs=[(0,y,11,y) for y in range(12)]
        comp=SimpleNamespace(component_id=7,color_index=0,area=144,bbox=(0,0,11,11),width=12,height=12,
            importance_mean=.08,importance_max=.12,edge_mean=.08,contour_mean=.08,protected_pixels=0,
            protected_ratio=0.0,horizontal_runs=runs,vertical_runs=[(x,0,x,11) for x in range(12)])
        o=opts(30);m=build_cost_model(o,(12,12),(12,12));packed,reason=ar._brush_pack_candidate(comp,cmap,o,m)
        self.assertIsNotNone(packed,reason)
        self.assertIn(28,packed['pruned_brush_sizes']);self.assertIn(16,packed['pruned_brush_sizes'])
        self.assertGreaterEqual(packed['ladder_candidates_evaluated'],2)
        self.assertGreaterEqual(len(set(packed['used_brush_sizes'])),2)

    def test_exact_swap_replaces_lower_value_component_when_refill_cannot_fit(self):
        cs=[choice(1,0,cost=.5,gain=10),choice(2,0,cost=.5,gain=1),choice(3,0,cost=10,gain=9)]
        seqs={1:entry(1,0,0,fake_cost=2),2:entry(2,0,180,fake_cost=2),3:entry(3,0,5,fake_cost=2)}
        with patch.object(ar,'_budget_seconds',return_value=(True,4.1,{},0.0,5.0)):
            _g,s,meta=ar._schedule(cs,seqs,(200,100),FakeModel(),{'brush_px':2,'paint_current_color':False},[])
        ids={e['component_id'] for e in s}
        self.assertIn(1,ids);self.assertIn(3,ids);self.assertNotIn(2,ids)
        self.assertGreaterEqual(meta['budget_swapped_components'],1)

    def test_version_stays_rc25(self):self.assertEqual(APP_VERSION,'1.0.145-rc25')

if __name__=='__main__':unittest.main()
''',encoding='utf-8')

print('Applied 10 Extra Fast improvements.')
