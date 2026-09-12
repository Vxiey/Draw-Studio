from pathlib import Path


def replace(path, old, new, count=1):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'rc6 anchor missing in {path}: {old[:160]!r}')
    p.write_text(text.replace(old, new, count), encoding='utf-8')


p = Path('AdaptiveRegionHybrid.py')
text = p.read_text(encoding='utf-8')
old = '''def _runs_from_mask(mask:np.ndarray,row_stride:int=1):
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
'''
new = '''def _runs_from_mask(mask:np.ndarray,row_stride:int=1,row_offset:int=0,orientation:str="horizontal"):
    """Return axis-aligned runs through a boolean centre mask.

    The mask contains only brush centres whose complete footprint is already
    proven to stay inside the source component.  Connecting consecutive true
    centres therefore remains safe for square browser brushes.
    """
    view=mask if orientation!="vertical" else mask.T
    h,w=view.shape;out=[]
    stride=max(1,int(row_stride));offset=int(row_offset)%stride
    for y in range(offset,h,stride):
        row=view[y];x=0
        while x<w:
            if not row[x]:x+=1;continue
            x0=x;x+=1
            while x<w and row[x]:x+=1
            if orientation=="vertical":
                out.append(((y,x0),(y,x-1)) if x-1!=x0 else ((y,x0),))
            else:
                out.append(((x0,y),(x-1,y)) if x-1!=x0 else ((x0,y),))
    return out


def _centers_touching_mask(mask:np.ndarray,brush_px:int) -> np.ndarray:
    """Return centres whose brush footprint touches at least one wanted pixel."""
    b=max(1,int(brush_px));lo=(b-1)//2;hi=b//2
    touch=np.zeros_like(mask,dtype=np.bool_);h,w=mask.shape
    for dy in range(-lo,hi+1):
        for dx in range(-lo,hi+1):
            shifted=np.zeros_like(mask,dtype=np.bool_)
            ys=slice(max(0,-dy),min(h,h-dy));yd=slice(max(0,dy),min(h,h+dy))
            xs=slice(max(0,-dx),min(w,w-dx));xd=slice(max(0,dx),min(w,w+dx))
            shifted[yd,xd]=mask[ys,xs]
            touch |= shifted
    return touch


def _candidate_paths_for_brush(target:np.ndarray,residual:np.ndarray,brush_px:int,*,
                               model,comp,phase:str,final_size:bool,cancelled=lambda:False):
    """Choose a high-coverage safe run layout for one verified brush size."""
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
            paths=_runs_from_mask(useful,row_stride=stride,row_offset=offset,orientation=orientation)
            if not paths:continue
            trial=np.zeros_like(target,dtype=np.bool_)
            for path in paths:_paint_path(trial,path,brush)
            if np.any(trial & ~target):continue
            gained=int(np.count_nonzero(trial & residual))
            if gained<=0:continue
            seq=_entry_sequence(comp.color_index,paths,phase=phase,comp=comp,brush_px=brush,
                                method=f"region-brush-pack-{brush}px")
            cost=max(.000001,float(model.sequence_cost(seq).total_seconds))
            candidate=(gained,-cost,-len(paths),orientation,offset,paths,trial,cost)
            if best is None or candidate[:3]>best[:3]:best=candidate
    if best is None:return [],np.zeros_like(target,dtype=np.bool_),0.0
    return list(best[5]),best[6],float(best[7])


def _brush_pack_candidate(comp,component_map,options,model,cancelled=lambda:False):
    """Pack one exact region with the verified browser brush ladder.

    Largest brushes are tried first, but every emitted centre is eroded against
    the complete source component and the final union is simulated pixel-for-
    pixel.  If the smallest verified brush cannot repair the residual exactly,
    the candidate is rejected and the existing connected-run planner remains
    authoritative.
    """
    default=max(1,int(options.get("brush_px") or 1))
    sizes,dynamic=verified_brush_sizes(str(options.get("profile_key") or ""),
                                       options.get("browser_brush_plan"),default)
    sizes=tuple(sorted({max(1,int(v)) for v in sizes},reverse=True))
    if not dynamic or len(sizes)<2:
        return None,"no verified multi-brush controls"
    smallest=min(sizes);largest=max(sizes)
    if comp.area<max(48,smallest*smallest*6):
        return None,"component too small for region brush packing"
    target=component_map==comp.component_id
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
            final_size=(brush==smallest),cancelled=cancelled)
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
    return {"sequence":sequence,"paths":flat_paths,"cost":cost,"brush_px":max(used),
            "method":"region-brush-pack","exact":True,"used_brush_sizes":tuple(used),
            "packing":per_size,"covered_pixels":int(np.count_nonzero(painted))}, \
           f"exact verified brush packing with sizes {tuple(used)}"
'''
if old not in text:
    raise SystemExit('rc6 broad candidate block missing')
text = text.replace(old, new, 1)

old = '''def _choose_component(comp,component_map,total_drawable,model,options,cancelled=lambda:False):
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
'''
new = '''def _choose_component(comp,component_map,total_drawable,model,options,cancelled=lambda:False):
    phase=_phase(comp,total_drawable);gain=_component_gain(comp,total_drawable)
    default=max(1,int(options.get("brush_px") or 1))
    verified,dynamic=verified_brush_sizes(str(options.get("profile_key") or ""),options.get("browser_brush_plan"),default)
    base_brush=min(verified) if dynamic and verified else default
    candidates=[]
    for orientation in ("horizontal","vertical"):
        paths,exact=_orientation_paths(comp,orientation,component_map,cancelled)
        if not exact:continue
        seq=_entry_sequence(comp.color_index,paths,phase=phase,comp=comp,
                            brush_px=base_brush,method=f"connected-{orientation}-runs")
        cost=model.sequence_cost(seq).total_seconds
        candidates.append((cost,len(paths),orientation,seq,paths,base_brush))
    packed,pack_reason=_brush_pack_candidate(comp,component_map,options,model,cancelled)
    if packed:
        candidates.append((packed["cost"],len(packed["paths"]),packed["method"],packed["sequence"],packed["paths"],packed["brush_px"]))
    if comp.area==1:
        x0,y0,_,_=comp.bbox;paths=[((x0,y0),)]
        seq=_entry_sequence(comp.color_index,paths,phase="detail",comp=comp,brush_px=base_brush,method="isolated-point")
        candidates.append((model.sequence_cost(seq).total_seconds,1,"isolated-point",seq,paths,base_brush))
    if not candidates:
        paths=_individual_paths(comp.horizontal_runs)
        seq=_entry_sequence(comp.color_index,paths,phase=phase,comp=comp,
                            brush_px=base_brush,method="safe-individual-runs")
        candidates=[(model.sequence_cost(seq).total_seconds,len(paths),"safe-individual-runs",seq,paths,base_brush)]
    best=min(candidates,key=lambda row:(row[0],row[1],row[2]))
    cost=max(.000001,float(best[0]))
    choice=RegionChoice(comp.component_id,comp.color_index,best[2],phase,comp.area,
                        float(comp.importance_mean),float(comp.edge_mean),comp.protected_pixels,
                        cost,gain,gain/(cost*1000.0),best[1],best[5],True,
                        f"minimum calibrated execution cost among {len(candidates)} exact candidate(s); {pack_reason}")
    diagnostics={"component_id":comp.component_id,
        "verified_brush_sizes":list(map(int,verified)),"base_brush_px":int(base_brush),
        "candidates":[{"method":c[2],"estimated_seconds":round(float(c[0]),6),"paths":int(c[1])} for c in candidates]}
    if packed:diagnostics["brush_packing"]={"used_brush_sizes":list(packed.get("used_brush_sizes") or ()),
        "packing":packed.get("packing") or (),"covered_pixels":int(packed.get("covered_pixels",0) or 0)}
    return choice,list(best[3]),diagnostics
'''
if old not in text:
    raise SystemExit('rc6 choose component block missing')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')

# Version bump and active version assertions only.
p = Path('Version.py')
version = p.read_text(encoding='utf-8')
if "APP_VERSION = '1.0.145-rc5'" not in version:
    raise SystemExit('rc6 expected rc5 version missing')
p.write_text(version.replace("APP_VERSION = '1.0.145-rc5'", "APP_VERSION = '1.0.145-rc6'", 1), encoding='utf-8')
for test in Path('.').glob('test_*.py'):
    lines=[];changed=False
    for line in test.read_text(encoding='utf-8').splitlines(True):
        if 'APP_VERSION' in line and '1.0.145-rc5' in line:
            line=line.replace('1.0.145-rc5','1.0.145-rc6');changed=True
        lines.append(line)
    if changed:test.write_text(''.join(lines),encoding='utf-8')

# Focused rc6 regression coverage.
Path('test_rc6_region_brush_packing.py').write_text(r'''import unittest
from types import SimpleNamespace
import numpy as np

from AdaptiveRegionHybrid import _brush_pack_candidate, _choose_component
from ExecutionCostModel import build_cost_model


def options():
    return {
        'profile_key':'gartic','brush_px':2,'speed':'Balanced','delay':0.0,
        'browser_brush_plan':{
            'target_position':(10,10),'confidence':0.99,
            'nominal_sizes':[2,4,8,16,28],
            'verified_sizes':[2,4,8,16,28],
            'control_positions':[(1,1),(2,1),(3,1),(4,1),(5,1)],
            'safe_guard_px':4,
        },
    }


def rectangle_component(width=120,height=80,cid=7):
    cmap=np.full((height,width),cid,dtype=np.int32)
    h_runs=[(0,y,width-1,y) for y in range(height)]
    v_runs=[(x,0,x,height-1) for x in range(width)]
    comp=SimpleNamespace(component_id=cid,color_index=0,area=width*height,bbox=(0,0,width-1,height-1),
        width=width,height=height,importance_mean=.08,importance_max=.12,edge_mean=.08,contour_mean=.08,
        protected_pixels=0,protected_ratio=0.0,horizontal_runs=h_runs,vertical_runs=v_runs)
    return comp,cmap


class Rc6RegionBrushPackingTests(unittest.TestCase):
    def test_gartic_five_size_plan_can_pack_without_one_px(self):
        comp,cmap=rectangle_component()
        model=build_cost_model(options(),(120,80),(120,80))
        packed,reason=_brush_pack_candidate(comp,cmap,options(),model)
        self.assertIsNotNone(packed,reason)
        self.assertTrue(packed['exact'])
        used=tuple(packed['used_brush_sizes'])
        self.assertGreaterEqual(len(set(used)),2)
        self.assertIn(28,used)
        self.assertNotIn(1,used)
        self.assertEqual(packed['covered_pixels'],comp.area)

    def test_irregular_one_pixel_tail_rejects_pack_and_keeps_safe_fallback(self):
        cid=3;cmap=np.full((30,40),-1,dtype=np.int32)
        cmap[4:26,4:36]=cid;cmap[15,36:40]=cid
        area=int(np.count_nonzero(cmap==cid))
        h_runs=[]
        for y in range(30):
            xs=np.flatnonzero(cmap[y]==cid)
            if len(xs):h_runs.append((int(xs[0]),y,int(xs[-1]),y))
        v_runs=[]
        for x in range(40):
            ys=np.flatnonzero(cmap[:,x]==cid)
            if len(ys):v_runs.append((x,int(ys[0]),x,int(ys[-1])))
        comp=SimpleNamespace(component_id=cid,color_index=0,area=area,bbox=(4,4,39,25),width=36,height=22,
            importance_mean=.2,importance_max=.4,edge_mean=.3,contour_mean=.3,protected_pixels=4,
            protected_ratio=4/area,horizontal_runs=h_runs,vertical_runs=v_runs)
        model=build_cost_model(options(),(40,30),(40,30))
        packed,reason=_brush_pack_candidate(comp,cmap,options(),model)
        self.assertIsNone(packed)
        self.assertIn('residual',reason)
        choice,seq,meta=_choose_component(comp,cmap,area,model,options())
        self.assertTrue(seq)
        self.assertNotEqual(choice.method,'region-brush-pack')
        self.assertEqual(meta['base_brush_px'],2)

    def test_isolated_path_never_requests_nonexistent_one_px_control(self):
        cid=9;cmap=np.array([[cid]],dtype=np.int32)
        comp=SimpleNamespace(component_id=cid,color_index=0,area=1,bbox=(0,0,0,0),width=1,height=1,
            importance_mean=1.0,importance_max=1.0,edge_mean=1.0,contour_mean=1.0,protected_pixels=1,
            protected_ratio=1.0,horizontal_runs=[(0,0,0,0)],vertical_runs=[(0,0,0,0)])
        model=build_cost_model(options(),(1,1),(1,1))
        choice,seq,meta=_choose_component(comp,cmap,1,model,options())
        self.assertTrue(seq)
        self.assertTrue(all(int(e.get('brush_px',0))==2 for e in seq))
        self.assertEqual(meta['base_brush_px'],2)


if __name__=='__main__':
    unittest.main()
''',encoding='utf-8')

print('rc6 patch applied')
