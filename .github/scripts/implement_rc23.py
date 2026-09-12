from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc23 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

p=Path('AdaptiveRegionHybrid.py'); text=p.read_text(encoding='utf-8')
start=text.index('def _candidate_paths_for_brush(')
end=text.index('\ndef _brush_pack_candidate(',start)
new_candidate=dedent(r'''
def _offset_paths(paths, origin):
    """Translate ROI-local paths back to absolute planner/canvas coordinates."""
    ox,oy=map(int,origin)
    if ox==0 and oy==0:return [tuple((int(x),int(y)) for x,y in path) for path in paths]
    return [tuple((int(x)+ox,int(y)+oy) for x,y in path) for path in paths]


def _candidate_paths_for_brush(target:np.ndarray,residual:np.ndarray,brush_px:int,*,
                               model,comp,phase:str,final_size:bool,origin=(0,0),cancelled=lambda:False):
    """Choose a high-coverage safe run layout inside one component ROI.

    Raster work stays ROI-local, but path cost and emitted geometry use absolute
    planner coordinates so DrawBot, ETA and cursor travel remain unchanged.
    """
    _cancel(cancelled)
    brush=max(1,int(brush_px))
    safe=_eroded_centers(target,brush)
    useful=safe & _centers_touching_mask(residual,brush)
    if not np.any(useful):return [],np.zeros_like(target,dtype=np.bool_),0.0
    stride=1 if final_size else brush
    offsets=(0,) if stride==1 else tuple(range(stride))
    best=None
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
            cost=max(.000001,float(model.sequence_cost(seq).total_seconds))
            candidate=(gained,-cost,-len(paths),orientation,offset,paths,trial,cost)
            if best is None or candidate[:3]>best[:3]:best=candidate
    if best is None:return [],np.zeros_like(target,dtype=np.bool_),0.0
    return list(best[5]),best[6],float(best[7])

''')
p.write_text(text[:start]+new_candidate+text[end:],encoding='utf-8')

p=Path('AdaptiveRegionHybrid.py'); text=p.read_text(encoding='utf-8')
start=text.index('def _brush_pack_candidate(')
end=text.index('\ndef _choose_component(',start)
new_pack=dedent(r'''
def _brush_pack_candidate(comp,component_map,options,model,cancelled=lambda:False):
    """Pack one exact region with verified browser brushes using bbox-local masks.

    Only temporary raster masks are cropped. Every emitted path is translated
    back to absolute planner coordinates before it is costed or returned.
    """
    default=max(1,int(options.get("brush_px") or 1))
    sizes,dynamic=verified_brush_sizes(str(options.get("profile_key") or ""),
                                       options.get("browser_brush_plan"),default)
    sizes=tuple(sorted({max(1,int(v)) for v in sizes},reverse=True))
    if not dynamic or len(sizes)<2:
        return None,"no verified multi-brush controls"
    smallest=min(sizes)
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

    painted=np.zeros_like(target,dtype=np.bool_)
    sequence=[];flat_paths=[];used=[];per_size=[]
    base_phase=_phase(comp,int(np.count_nonzero(component_map>=0)))
    for brush in sizes:
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
    if np.any(painted & ~target):
        return None,"region brush packing spilled outside component"
    missing=int(np.count_nonzero(target & ~painted))
    if missing or not np.array_equal(painted,target):
        return None,f"smallest verified brush cannot exactly repair {missing} residual pixel(s)"
    if len(set(used))<2:
        return None,"multi-brush packing produced no useful brush transition"
    cost=model.sequence_cost(sequence).total_seconds
    roi_pixels=int(target.size);canvas_pixels=int(component_map.size)
    reduction=max(0.0,1.0-(roi_pixels/max(1,canvas_pixels)))
    return {"sequence":sequence,"paths":flat_paths,"cost":cost,"brush_px":max(used),
            "method":"region-brush-pack","exact":True,"used_brush_sizes":tuple(used),
            "packing":per_size,"covered_pixels":int(np.count_nonzero(painted)),
            "packing_roi_bbox":(x0,y0,x1,y1),"packing_workspace_pixels":roi_pixels,
            "packing_canvas_pixels":canvas_pixels,
            "packing_workspace_reduction_percent":round(reduction*100.0,4)},\
            f"exact verified brush packing with sizes {tuple(used)} in ROI {(x0,y0,x1,y1)}"

''')
p.write_text(text[:start]+new_pack+text[end:],encoding='utf-8')

# Surface ROI diagnostics in component metadata without changing selection.
replace('AdaptiveRegionHybrid.py',
'''    if packed:diagnostics["brush_packing"]={"used_brush_sizes":list(packed.get("used_brush_sizes") or ()),\n        "packing":packed.get("packing") or (),"covered_pixels":int(packed.get("covered_pixels",0) or 0)}\n''',
'''    if packed:diagnostics["brush_packing"]={"used_brush_sizes":list(packed.get("used_brush_sizes") or ()),\n        "packing":packed.get("packing") or (),"covered_pixels":int(packed.get("covered_pixels",0) or 0),\n        "roi_bbox":packed.get("packing_roi_bbox"),\n        "workspace_pixels":int(packed.get("packing_workspace_pixels",0) or 0),\n        "canvas_pixels":int(packed.get("packing_canvas_pixels",0) or 0),\n        "workspace_reduction_percent":float(packed.get("packing_workspace_reduction_percent",0.0) or 0.0)}\n''')

replace('Version.py',"APP_VERSION = '1.0.145-rc22'","APP_VERSION = '1.0.145-rc23'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc22"','#define MyAppVersion "1.0.145-rc23"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc22' in raw:test.write_text(raw.replace('1.0.145-rc22','1.0.145-rc23'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc22','1.0.145-rc23'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc23 — Region Brush ROI Packing\n\n- Move Adaptive Region Hybrid multi-brush raster work from full-canvas temporary masks to each connected component's exact bbox ROI.\n- Translate every generated ROI-local path back to absolute planner coordinates before execution-cost evaluation and return.\n- Preserve exact brush-footprint erosion, even-brush geometry, residual repair and full-component fallback behavior.\n- Add ROI workspace diagnostics so large sparse canvases expose the temporary-mask reduction.\n- Keep the verified Gartic brush ladder and real execution-cost selection unchanged.\n- Reduce CPU/RAM pressure without changing selected source pixels or allowing brush spill.\n'''
Path('RELEASE-NOTES-v1.0.145-rc23.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc23 — Region Brush ROI Packing\n\n- Multi-brush connected-region packing now allocates temporary masks only for each component bbox.\n- ROI paths are translated back to global coordinates before cost/execution.\n- Exact coverage, spill rejection and residual fallback remain authoritative.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from types import SimpleNamespace
import numpy as np

from AdaptiveRegionHybrid import _brush_pack_candidate,_paint_path
from ExecutionCostModel import build_cost_model
from Version import APP_VERSION


def options():
    return {'profile_key':'gartic','brush_px':2,'speed':'Balanced','delay':0.0,
            'browser_brush_plan':{'target_position':(10,10),'confidence':.99,
                'nominal_sizes':[2,4,8,16,28],'verified_sizes':[2,4,8,16,28],
                'control_positions':[(1,1),(2,1),(3,1),(4,1),(5,1)],'safe_guard_px':4}}


def offset_rectangle(canvas=(1400,900),origin=(900,610),size=(120,80),cid=7):
    w,h=canvas;ox,oy=origin;rw,rh=size
    cmap=np.full((h,w),-1,dtype=np.int32);cmap[oy:oy+rh,ox:ox+rw]=cid
    h_runs=[(ox,y,ox+rw-1,y) for y in range(oy,oy+rh)]
    v_runs=[(x,oy,x,oy+rh-1) for x in range(ox,ox+rw)]
    comp=SimpleNamespace(component_id=cid,color_index=0,area=rw*rh,
        bbox=(ox,oy,ox+rw-1,oy+rh-1),width=rw,height=rh,
        importance_mean=.08,importance_max=.12,edge_mean=.08,contour_mean=.08,
        protected_pixels=0,protected_ratio=0.0,horizontal_runs=h_runs,vertical_runs=v_runs)
    return comp,cmap


class Rc23RegionBrushRoiTests(unittest.TestCase):
    def test_far_offset_component_emits_global_paths_and_exact_full_canvas_coverage(self):
        comp,cmap=offset_rectangle();opts=options()
        model=build_cost_model(opts,(cmap.shape[1],cmap.shape[0]),(cmap.shape[1],cmap.shape[0]))
        packed,reason=_brush_pack_candidate(comp,cmap,opts,model)
        self.assertIsNotNone(packed,reason);self.assertTrue(packed['exact'])
        x0,y0,x1,y1=comp.bbox
        self.assertTrue(all(x0<=x<=x1 and y0<=y<=y1 for e in packed['sequence'] for x,y in e['path']))
        painted=np.zeros(cmap.shape,dtype=np.bool_)
        for e in packed['sequence']:_paint_path(painted,e['path'],int(e['brush_px']))
        self.assertTrue(np.array_equal(painted,cmap==comp.component_id))

    def test_workspace_is_component_bbox_not_full_canvas(self):
        comp,cmap=offset_rectangle(canvas=(2000,1200),origin=(1500,850),size=(100,60));opts=options()
        model=build_cost_model(opts,(2000,1200),(2000,1200))
        packed,reason=_brush_pack_candidate(comp,cmap,opts,model)
        self.assertIsNotNone(packed,reason)
        self.assertEqual(packed['packing_workspace_pixels'],100*60)
        self.assertEqual(packed['packing_canvas_pixels'],2000*1200)
        self.assertGreater(packed['packing_workspace_reduction_percent'],99.0)
        self.assertEqual(tuple(packed['packing_roi_bbox']),comp.bbox)

    def test_roi_keeps_verified_multibrush_ladder(self):
        comp,cmap=offset_rectangle();opts=options();model=build_cost_model(opts,(1400,900),(1400,900))
        packed,reason=_brush_pack_candidate(comp,cmap,opts,model)
        self.assertIsNotNone(packed,reason)
        used=set(packed['used_brush_sizes'])
        self.assertIn(28,used);self.assertGreaterEqual(len(used),2);self.assertNotIn(1,used)

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc23')


if __name__=='__main__':unittest.main()
''')
Path('test_rc23_region_brush_roi.py').write_text(TEST,encoding='utf-8')
