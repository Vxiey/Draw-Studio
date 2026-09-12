from pathlib import Path

p=Path('AdaptiveRegionHybrid.py')
text=p.read_text(encoding='utf-8')

text=text.replace(
'''            cost=max(.000001,float(model.sequence_cost(seq).total_seconds))''',
'''            cost=max(.000001,float(model.sequence_cost(
                seq, initial_color=int(comp.color_index), initial_brush=brush).total_seconds))''',
1)
text=text.replace(
'''    cost=model.sequence_cost(sequence).total_seconds
    roi_pixels=int(target.size);canvas_pixels=int(component_map.size)''',
'''    cost=model.sequence_cost(
        sequence, initial_color=int(comp.color_index), initial_brush=default).total_seconds
    roi_pixels=int(target.size);canvas_pixels=int(component_map.size)''',
1)

old='''        cost=model.sequence_cost(seq).total_seconds
        candidates.append((cost,len(paths),orientation,seq,paths,base_brush))'''
new='''        cost=model.sequence_cost(
            seq, initial_color=int(comp.color_index), initial_brush=default).total_seconds
        candidates.append((cost,len(paths),orientation,seq,paths,base_brush))'''
if text.count(old)!=1: raise SystemExit(f'orientation cost anchor count={text.count(old)}')
text=text.replace(old,new)

old='''        candidates.append((model.sequence_cost(seq).total_seconds,1,"isolated-point",seq,paths,base_brush))'''
new='''        candidates.append((model.sequence_cost(
            seq, initial_color=int(comp.color_index), initial_brush=default).total_seconds,
            1,"isolated-point",seq,paths,base_brush))'''
if text.count(old)!=1: raise SystemExit(f'isolated cost anchor count={text.count(old)}')
text=text.replace(old,new)

old='''        candidates=[(model.sequence_cost(seq).total_seconds,len(paths),"safe-individual-runs",seq,paths,base_brush)]'''
new='''        candidates=[(model.sequence_cost(
            seq, initial_color=int(comp.color_index), initial_brush=default).total_seconds,
            len(paths),"safe-individual-runs",seq,paths,base_brush)]'''
if text.count(old)!=1: raise SystemExit(f'fallback cost anchor count={text.count(old)}')
text=text.replace(old,new)

start=text.index('def _budget_seconds(options,model,choices,fill_regions):')
end=text.index('\ndef simulate_quantized_plan', start)
replacement=r'''def _budget_seconds(options,model,choices,fill_regions,image_size,fitted):
    active=bool(options.get("time_budget_active"))
    mode=str(options.get("time_budget_mode") or "")
    if mode in ("Unlimited","Off"):active=False
    try:limit=float(options.get("max_seconds") or options.get("manual_max_seconds") or 180)
    except Exception:limit=180.0
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
    reserve=max(1.5,limit*.045) if active else 0.0
    usable=max(0.0,limit-outside_seconds-reserve) if active else float('inf')
    return active,usable,{
        "base_fixed":fixed.as_dict(),"fill":fill_meta,
        "fill_palette_seconds":round(fill_palette_seconds,6),
        "adaptive_verification_seconds":round(verification_seconds,6),
        "canvas_clear_seconds":round(clear_seconds,6),
        "outside_sequence_seconds":round(outside_seconds,6),
    },reserve,limit


def _schedule(choices, sequences_by_component, size, model,options,fill_regions):
    active,usable,fixed_meta,reserve,limit=_budget_seconds(
        options,model,choices,fill_regions,size,size)
    weights={"foundation":1.25,"structure":1.18,"detail":1.04,"correction":.78}
    phase_order={p:i for i,p in enumerate(PHASES)}
    by_id={c.component_id:c for c in choices}

    def order_rows(ids):
        rows=[by_id[i] for i in ids if i in by_id]
        rows.sort(key=lambda c:(phase_order[c.phase],int(c.color_index),
                                -c.gain_per_ms,-c.visual_gain,c.component_id))
        return rows

    def build_sequence(ids):
        sequence=[];serial=0
        for c in order_rows(ids):
            for raw in sequences_by_component[c.component_id]:
                e=dict(raw);e["serial"]=serial;serial+=1;sequence.append(e)
        return sequence

    try:initial_brush=max(1,int(options.get("brush_px") or 1))
    except Exception:initial_brush=1

    seed_ids=set()
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
                selected.add(c.component_id);seed_ids.add(c.component_id);used+=c.estimated_seconds
        rest=[c for c in choices if c.component_id not in selected]
        rest.sort(key=lambda c:(-(c.gain_per_ms*weights[c.phase]),-c.visual_gain,c.component_id))
        for c in rest:
            if used+c.estimated_seconds<=usable:
                selected.add(c.component_id);used+=c.estimated_seconds

    sequence=build_sequence(selected)
    seq_cost=model.sequence_cost(sequence,initial_brush=initial_brush)
    trimmed=[];refilled=[]

    if active:
        protected_ids={c.component_id for c in choices
                       if c.component_id in selected and c.protected_pixels and c.importance>=.50}
        while selected and seq_cost.total_seconds>usable+1e-9:
            rows=order_rows(selected)
            removable=[c for c in rows if c.component_id not in seed_ids and c.component_id not in protected_ids]
            if not removable: removable=[c for c in rows if c.component_id not in seed_ids]
            if not removable: removable=rows
            victim=min(removable,key=lambda c:(c.gain_per_ms*weights[c.phase],c.visual_gain,-c.estimated_seconds,c.component_id))
            selected.remove(victim.component_id);trimmed.append(victim.component_id)
            sequence=build_sequence(selected)
            seq_cost=model.sequence_cost(sequence,initial_brush=initial_brush)

        omitted=[c for c in choices if c.component_id not in selected]
        omitted.sort(key=lambda c:(-(c.gain_per_ms*weights[c.phase]),-c.visual_gain,c.component_id))
        for c in omitted[:64]:
            trial=set(selected);trial.add(c.component_id)
            trial_sequence=build_sequence(trial)
            trial_cost=model.sequence_cost(trial_sequence,initial_brush=initial_brush)
            if trial_cost.total_seconds<=usable+1e-9:
                selected=trial;sequence=trial_sequence;seq_cost=trial_cost;refilled.append(c.component_id)

    groups=[[] for _ in range(max([c.color_index for c in choices],default=-1)+1)]
    for e in sequence:
        while len(groups)<=int(e["color_index"]):groups.append([])
        groups[int(e["color_index"])].append(tuple(e["path"]))
    utilization=(seq_cost.total_seconds/usable*100.0) if active and usable>0 else 0.0
    return groups,sequence,{
        "deadline_active":active,"deadline_seconds":round(limit,4),"usable_path_seconds":round(usable,4),
        "fixed_overhead":fixed_meta,"safety_reserve_seconds":round(reserve,4),
        "selected_components":len(selected),"total_components":len(choices),
        "dropped_components":len(choices)-len(selected),
        "selected_path_cost_seconds":round(seq_cost.total_seconds,6),
        "selected_operation_cost":seq_cost.as_dict(),
        "exact_budget_guard":True,"budget_trimmed_components":len(trimmed),
        "budget_refilled_components":len(refilled),"budget_utilization_percent":round(utilization,3),
        "palette_switches":int(seq_cost.palette_switches),"brush_switches":int(seq_cost.brush_switches),
        "phase_color_batching":True,
    }
'''
text=text[:start]+replacement+text[end:]
p.write_text(text,encoding='utf-8')

Path('test_extra_fast_budget_accounting_rc25.py').write_text(r'''import unittest
from AdaptiveRegionHybrid import RegionChoice,_schedule
from ExecutionCostModel import build_cost_model
from Version import APP_VERSION

def choice(cid,color,cost=.01,gain=.1,phase='structure',protected=0,importance=.3):
    return RegionChoice(cid,color,'test',phase,100,importance,.2,protected,cost,gain,gain/(cost*1000),1,2,True,'test')

def seq(cid,color,brush=2,length=120,phase='structure'):
    y=cid*3+1
    return [{'color_index':color,'brush_px':brush,'path':((1,y),(length,y)),'phase':phase,'component_id':cid}]

def options(limit=8.0):
    return {'profile_key':'gartic','brush_px':2,'speed':'Balanced','delay':0.0,'time_budget_active':True,
            'time_budget_mode':'Custom','max_seconds':limit,'paint_current_color':False,
            'adaptive_color_verification':False,'fill_tool_available':False}

class ExtraFastBudgetAccountingRc25Tests(unittest.TestCase):
    def test_local_component_cost_does_not_pay_first_palette_switch_twice(self):
        opts=options();model=build_cost_model(opts,(200,120),(200,120));s=seq(1,3)
        global_cost=model.sequence_cost(s,initial_brush=2).total_seconds
        local_cost=model.sequence_cost(s,initial_color=3,initial_brush=2).total_seconds
        self.assertGreater(global_cost,local_cost)
        self.assertAlmostEqual(global_cost-local_cost,model.switch_cost('palette_change'),places=6)

    def test_same_phase_components_are_colour_batched(self):
        opts=options(30);model=build_cost_model(opts,(300,180),(300,180))
        choices=[choice(1,0),choice(2,1),choice(3,0),choice(4,1)]
        seqs={c.component_id:seq(c.component_id,c.color_index,length=20) for c in choices}
        _groups,execution,meta=_schedule(choices,seqs,(300,180),model,opts,[])
        colors=[e['color_index'] for e in execution]
        transitions=sum(a!=b for a,b in zip(colors,colors[1:]))
        self.assertLessEqual(transitions,1);self.assertTrue(meta['phase_color_batching'])
        self.assertEqual(meta['palette_switches'],transitions+1)

    def test_exact_final_sequence_never_exceeds_usable_deadline(self):
        opts=options(7.0);model=build_cost_model(opts,(500,300),(500,300))
        choices=[choice(i,i%3,cost=.001,gain=.05+i*.001) for i in range(1,25)]
        seqs={c.component_id:seq(c.component_id,c.color_index,length=450) for c in choices}
        _groups,_execution,meta=_schedule(choices,seqs,(500,300),model,opts,[])
        self.assertTrue(meta['exact_budget_guard'])
        self.assertLessEqual(meta['selected_path_cost_seconds'],meta['usable_path_seconds']+1e-6)
        self.assertGreater(meta['budget_trimmed_components'],0)

    def test_brush_switches_are_in_exact_schedule_cost(self):
        opts=options(30);model=build_cost_model(opts,(300,180),(300,180))
        choices=[choice(1,0),choice(2,0)];seqs={1:seq(1,0,2,length=30),2:seq(2,0,28,length=30)}
        _groups,_execution,meta=_schedule(choices,seqs,(300,180),model,opts,[])
        self.assertGreaterEqual(meta['brush_switches'],1)
        self.assertGreater(meta['selected_operation_cost']['brush_seconds'],0)

    def test_version_stays_rc25(self): self.assertEqual(APP_VERSION,'1.0.145-rc25')

if __name__=='__main__':unittest.main()
''',encoding='utf-8')
print('Extra Fast budget accounting patch applied.')
