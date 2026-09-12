from pathlib import Path


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text: raise SystemExit(f'rc10 anchor missing in {path}: {old[:140]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

p=Path('PixelAccuracyEngine.py');text=p.read_text(encoding='utf-8')
anchor='''def refine_with_corrections(pixel_map: PixelMap, execution_sequence: Sequence[dict], palette_rgb: Sequence[Sequence[int]], *,\n'''
insert=r'''def region_accuracy_scores(pixel_map: PixelMap, result: SimulationResult, *, max_regions: int = 64,
                           cancelled=lambda: False) -> dict:
    """Measure planned execution accuracy per exact connected target region."""
    from PixelStrokeEngine import connected_components
    components,cmap,_meta=connected_components(pixel_map,cpu_workers=1,cancelled=cancelled)
    desired=np.asarray(pixel_map.palette_index,dtype=np.int16)
    simulated=np.asarray(result.simulated_index,dtype=np.int16)
    covered=np.asarray(result.coverage_count)>0
    edge=np.asarray(pixel_map.edge_map,dtype=np.float32)>=.5
    protected=np.asarray(pixel_map.protected_mask,dtype=bool)
    rows=[];weighted=0.0;weighted_area=0
    def pct(n,d,fallback):
        return float(fallback) if int(d)<=0 else float(n)/float(d)*100.0
    for serial,comp in enumerate(components):
        if serial%64==0 and cancelled():raise InterruptedError()
        mask=cmap==int(comp.component_id);area=int(np.count_nonzero(mask))
        if area<=0:continue
        correct=mask & (simulated==desired)
        coverage=mask & covered
        color_acc=pct(np.count_nonzero(correct),area,0.0)
        coverage_acc=pct(np.count_nonzero(coverage),area,0.0)
        edge_mask=mask & edge;protected_mask=mask & protected
        edge_acc=pct(np.count_nonzero(correct & edge_mask),np.count_nonzero(edge_mask),color_acc)
        detail_acc=pct(np.count_nonzero(correct & protected_mask),np.count_nonzero(protected_mask),color_acc)
        score=.40*color_acc+.25*coverage_acc+.20*edge_acc+.15*detail_acc
        row={'component_id':int(comp.component_id),'color_index':int(comp.color_index),'area':area,
             'bbox':tuple(map(int,comp.bbox)),'score':round(score,4),
             'color_accuracy_percent':round(color_acc,4),'coverage_percent':round(coverage_acc,4),
             'edge_accuracy_percent':round(edge_acc,4),'protected_detail_percent':round(detail_acc,4),
             'error_pixels':int(area-np.count_nonzero(correct)),
             'protected_pixels':int(np.count_nonzero(protected_mask))}
        rows.append(row);weighted+=score*area;weighted_area+=area
    rows.sort(key=lambda row:(float(row['score']),-int(row['area']),int(row['component_id'])))
    limit=max(1,int(max_regions))
    scores=[float(row['score']) for row in rows]
    return {'region_count':len(rows),'weighted_score':round(weighted/max(1,weighted_area),4),
            'mean_score':round(sum(scores)/max(1,len(scores)),4) if rows else 100.0,
            'minimum_score':round(min(scores),4) if rows else 100.0,
            'worst_regions':rows[:limit],
            'score_formula':'0.40*color + 0.25*coverage + 0.20*edge + 0.15*protected_detail'}


'''+anchor
if anchor not in text:raise SystemExit('rc10 refine anchor missing')
text=text.replace(anchor,insert,1)
old='''                            brush_px: int = 1, max_passes: int = 2, min_improvement: float = .0001,\n                            correction_brush_px: int | None = None,\n                            max_total_paths: int | None = None, gpu_mode: str = "CPU",\n'''
new='''                            brush_px: int = 1, max_passes: int = 2, min_improvement: float = .0001,\n                            correction_brush_px: int | None = None,\n                            max_total_paths: int | None = None, min_repaired_pixels_per_path: float = .05,\n                            gpu_mode: str = "CPU",\n'''
if old not in text:raise SystemExit('rc10 signature anchor missing')
text=text.replace(old,new,1)
old='''        accepted=(after>before+float(min_improvement)) or (after>=before and after_errors<before_errors)\n        pass_meta.append({'pass':pass_number,'generated_paths':len(corrections),'accepted':bool(accepted),\n                          'before_accuracy':round(before,4),'after_accuracy':round(after,4),\n                          'before_errors':before_errors,'after_errors':after_errors})\n        if not accepted:break\n'''
new='''        accuracy_gain=after-before\n        errors_repaired=max(0,before_errors-after_errors)\n        path_count=max(1,len(corrections))\n        repaired_per_path=errors_repaired/path_count\n        gain_per_path=max(0.0,accuracy_gain)/path_count\n        accepted=(after>before+float(min_improvement)) or (after>=before and after_errors<before_errors)\n        efficiency_floor=max(0.0,float(min_repaired_pixels_per_path))\n        inefficient=(pass_number>1 and len(corrections)>=8 and errors_repaired>0 and\n                     repaired_per_path<efficiency_floor and accuracy_gain<max(.005,float(min_improvement)*4.0))\n        if inefficient:accepted=False\n        pass_meta.append({'pass':pass_number,'generated_paths':len(corrections),'accepted':bool(accepted),\n                          'before_accuracy':round(before,4),'after_accuracy':round(after,4),\n                          'accuracy_gain':round(accuracy_gain,6),'accuracy_gain_per_path':round(gain_per_path,8),\n                          'before_errors':before_errors,'after_errors':after_errors,\n                          'errors_repaired':int(errors_repaired),'repaired_pixels_per_path':round(repaired_per_path,6),\n                          'efficiency_floor':round(efficiency_floor,6),\n                          'stop_reason':'low marginal correction gain' if inefficient else ('accepted' if accepted else 'no accuracy improvement')})\n        if not accepted:break\n'''
if old not in text:raise SystemExit('rc10 acceptance anchor missing')
text=text.replace(old,new,1)
old="""    final=dict(current.metrics)\n    meta={\n"""
new="""    final=dict(current.metrics)\n    try:\n        region_meta=region_accuracy_scores(pixel_map,current,max_regions=64,cancelled=cancelled)\n    except InterruptedError:raise\n    except Exception as exc:\n        region_meta={'region_count':0,'weighted_score':None,'mean_score':None,'minimum_score':None,\n                     'worst_regions':[],'reason':f'{type(exc).__name__}: {exc}'}\n    meta={\n"""
if old not in text:raise SystemExit('rc10 final meta anchor missing')
text=text.replace(old,new,1)
old="""        'initial_accuracy_percent':initial['pixel_accuracy_percent'],\n        'final_accuracy_percent':final['pixel_accuracy_percent'],'initial_error_pixels':initial['error_pixels'],\n        'final_error_pixels':final['error_pixels'],'passes':pass_meta,**final,\n"""
new="""        'initial_accuracy_percent':initial['pixel_accuracy_percent'],\n        'final_accuracy_percent':final['pixel_accuracy_percent'],'initial_error_pixels':initial['error_pixels'],\n        'final_error_pixels':final['error_pixels'],'passes':pass_meta,\n        'region_accuracy':region_meta,'region_accuracy_score':region_meta.get('weighted_score'),\n        'worst_region_accuracy_score':region_meta.get('minimum_score'),\n        'correction_efficiency_floor':max(0.0,float(min_repaired_pixels_per_path)),**final,\n"""
if old not in text:raise SystemExit('rc10 meta fields anchor missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

Path('test_rc10_pixel_accuracy_2.py').write_text(r'''import unittest
import numpy as np
from PixelAccuratePlanner import PixelMap
from PixelAccuracyEngine import simulate_strokes,refine_with_corrections,region_accuracy_scores
from Version import APP_VERSION

PALETTE=((255,255,255),(0,0,0),(255,0,0))

def pm(index,protected=None,edges=None):
    idx=np.asarray(index,dtype=np.int16);h,w=idx.shape;drawable=idx>=0
    safe=np.where(drawable,idx,0).astype(np.int16);rgb=np.zeros((h,w,3),np.uint8)
    if protected is None:protected=np.zeros((h,w),bool)
    if edges is None:edges=np.where(drawable,.1,0).astype(np.float32)
    importance=np.where(drawable,.3,0).astype(np.float32)
    return PixelMap(w,h,rgb,safe,drawable,np.asarray(edges,np.float32),importance,np.asarray(protected,bool),{})

def e(color,path):return {'color_index':color,'path':tuple(path),'phase':'fine_detail','serial':0,'component_id':0}

class Rc10PixelAccuracy2Tests(unittest.TestCase):
    def test_region_scores_find_worst_missing_component(self):
        pixel_map=pm([[1,1,-1,2,2]])
        sim=simulate_strokes(pixel_map,[e(1,((0,0),(1,0)))],PALETTE,brush_px=1)
        meta=region_accuracy_scores(pixel_map,sim)
        self.assertEqual(meta['region_count'],2)
        self.assertLess(meta['minimum_score'],meta['weighted_score'])
        self.assertEqual(meta['worst_regions'][0]['color_index'],2)
        self.assertGreater(meta['worst_regions'][0]['error_pixels'],0)

    def test_correction_pass_reports_marginal_gain(self):
        pixel_map=pm([[1,1,1,1]])
        result=refine_with_corrections(pixel_map,[e(1,((0,0),(1,0)))],PALETTE,brush_px=1,max_passes=2)
        self.assertTrue(result['metadata']['passes'])
        row=result['metadata']['passes'][0]
        for key in ('accuracy_gain','accuracy_gain_per_path','errors_repaired','repaired_pixels_per_path','stop_reason'):
            self.assertIn(key,row)
        self.assertEqual(result['metadata']['region_accuracy']['region_count'],1)

    def test_region_score_weights_protected_detail(self):
        protected=np.array([[False,True]],bool);edges=np.array([[.1,.9]],np.float32)
        pixel_map=pm([[1,1]],protected=protected,edges=edges)
        sim=simulate_strokes(pixel_map,[e(1,((0,0),))],PALETTE,brush_px=1)
        row=region_accuracy_scores(pixel_map,sim)['worst_regions'][0]
        self.assertLess(row['protected_detail_percent'],100.0)
        self.assertLess(row['edge_accuracy_percent'],100.0)

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc10')

if __name__=='__main__':unittest.main()
''',encoding='utf-8')

replace('Version.py',"APP_VERSION = '1.0.145-rc9'","APP_VERSION = '1.0.145-rc10'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc9"','#define MyAppVersion "1.0.145-rc10"')
readme=Path('README.md');readme.write_text(readme.read_text(encoding='utf-8').replace('1.0.145-rc9','1.0.145-rc10'),encoding='utf-8')
for test in Path('.').glob('test_*.py'):
    if test.name=='test_rc10_pixel_accuracy_2.py':continue
    t=test.read_text(encoding='utf-8')
    if '1.0.145-rc9' in t:test.write_text(t.replace('1.0.145-rc9','1.0.145-rc10'),encoding='utf-8')
history=Path('VERSION-HISTORY.md');h=history.read_text(encoding='utf-8')
heading='# Image Draw Bot v1.0.145-rc10 — Pixel Accuracy 2.0'
if heading not in h:
    history.write_text(heading+'\n\n- Added per-connected-region accuracy scoring across color, coverage, edges and protected detail.\n- Pixel correction passes now report marginal accuracy gain and repaired pixels per correction path.\n- Later correction passes can stop when simulated marginal repair efficiency becomes negligible.\n- Existing coverage maps, pixel error maps, CPU/GPU simulation and correction safety remain authoritative.\n\n'+h,encoding='utf-8')
Path('RELEASE-NOTES-v1.0.145-rc10.md').write_text('''# Image Draw Bot v1.0.145-rc10 — Pixel Accuracy 2.0\n\n- Add connected-region accuracy scores so poor local regions are visible even when global Pixel Accuracy is high.\n- Score color correctness, coverage, edges and protected details per region.\n- Record marginal correction gain, repaired pixels and gain per path for every correction pass.\n- Stop later correction refinement when the simulated quality gain no longer justifies correction work.\n- Preserve the existing CPU/GPU stroke simulation, coverage and pixel-error safety pipeline.\n''',encoding='utf-8')
print('rc10 patch applied')
