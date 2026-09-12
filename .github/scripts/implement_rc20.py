from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc20 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

# Pixel Accurate keeps its exact geometry and phase contract. Only the cost source
# used for H/V choice, bounded path splitting and component scheduling changes.
replace('PixelStrokeEngine.py',
'''    cost_model=None\n    if isinstance(options,dict) and str(options.get("adaptive_hybrid_cost","Auto")) != "Off":\n        try:\n            from HybridCostModel import build_cost_model\n            cost_model=build_cost_model(options)\n        except Exception:\n            cost_model=None\n''',
'''    cost_model=None\n    if isinstance(options,dict) and str(options.get("adaptive_hybrid_cost","Auto")) != "Off":\n        try:\n            from ExecutionCostModel import build_cost_model\n            # DrawBot already provides exact _hybrid_scale_x/y for Pixel Accurate.\n            # Direct tests that do not have a target canvas remain source-space 1:1.\n            cost_model=build_cost_model(options,(pixel_map.width,pixel_map.height),\n                                        (pixel_map.width,pixel_map.height))\n        except Exception:\n            cost_model=None\n''')

# Avoid a second travel formula. Intrinsic component cost is cached once; dynamic
# entry travel is exactly the first path's stateful cursor delta. This preserves
# the scheduler's bounded 72-candidate window without repeatedly walking all paths.
replace('PixelStrokeEngine.py',
'''                else:\n                    seconds=intrinsic[comp.component_id]\n                    if cursor is not None:\n                        seconds+=cost_model.travel_seconds(cursor,start)\n                    if current_color not in (None,comp.color_index):seconds+=float(cost_model.color_change_seconds)\n                    # Keep the multi-pass contract, but within each phase choose\n                    # the component with highest visual value per millisecond.\n                    value=max(.001,float(_priority(comp)))\n                    cost=(seconds/max(.001,value))+i*1e-9\n''',
'''                else:\n                    seconds=intrinsic[comp.component_id]\n                    if cursor is not None and comp.paths and comp.paths[0]:\n                        first=comp.paths[0]\n                        # paths_seconds() already includes the first path's base\n                        # travel/settle term. Add only the real stateful entry delta.\n                        moved=float(cost_model.path_seconds(first,cursor=cursor))\n                        base=float(cost_model.path_seconds(first,cursor=None))\n                        seconds+=max(0.0,moved-base)\n                    if current_color not in (None,comp.color_index):\n                        seconds+=float(cost_model.color_change_seconds)\n                    # Keep the multi-pass contract, but within each phase choose\n                    # the component with highest visual value per millisecond.\n                    value=max(.001,float(_priority(comp)))\n                    cost=(seconds/max(.001,value))+i*1e-9\n''')

# Do not maintain a second scheduler ETA accumulator. Cost the final ordered base
# Pixel sequence once with the shared stateful model. AdaptiveBrushEngine and
# correction passes later update the actual final sequence, whose visible ETA is
# independently costed again by DrawTimeEstimate.
replace('PixelStrokeEngine.py',
'''            if cost_model is not None and current_color != comp.color_index:\n                estimated_total += cost_model.color_change_seconds\n            for path in comp.paths:\n                if cost_model is not None:\n                    estimated_total += cost_model.path_seconds(path,cursor=cursor)\n                execution_groups[comp.color_index].append(path)\n''',
'''            for path in comp.paths:\n                execution_groups[comp.color_index].append(path)\n''')
replace('PixelStrokeEngine.py',
'''            current_color = comp.color_index\n\n    return execution_groups, sequence, {\n''',
'''            current_color = comp.color_index\n\n    if cost_model is not None:\n        try:\n            _initial_brush=max(1,int(getattr(cost_model,'options',{}).get('brush_px',1) or 1))\n            estimated_total=float(cost_model.sequence_cost(\n                sequence,initial_brush=_initial_brush).total_seconds)\n        except Exception:\n            # The geometry/order remains valid even if diagnostics cannot be costed.\n            estimated_total=sum(float(cost_model.paths_seconds(c.paths)) for c in components if c.paths)\n\n    return execution_groups, sequence, {\n''')
replace('PixelStrokeEngine.py',
'''        "cost_aware": bool(cost_model is not None),\n        "cost_model": cost_model.as_dict() if cost_model is not None else None,\n''',
'''        "cost_aware": bool(cost_model is not None),\n        "cost_policy": "ExecutionCostModel stateful v3" if cost_model is not None else "legacy geometry scheduler",\n        "cost_model": cost_model.as_dict() if cost_model is not None else None,\n''')

# Version / release surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc19'","APP_VERSION = '1.0.145-rc20'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc19"','#define MyAppVersion "1.0.145-rc20"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc19' in raw:test.write_text(raw.replace('1.0.145-rc19','1.0.145-rc20'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc19','1.0.145-rc20'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc20 — Pixel Accurate Unified Execution Cost\n\n- Move PixelStrokeEngine H/V orientation, deadline path splitting and bounded component scheduling to the shared stateful `ExecutionCostModel`.\n- Reuse DrawBot's exact PixelMap-to-canvas scale overrides so Pixel Accurate optimizes real mouse execution time rather than source-space run count.\n- Keep exact PixelMap coverage, connected-component safety, protected-detail phases, correction passes and Pixel Accuracy Score unchanged.\n- Keep the 72-component bounded scheduler window; dynamic cursor travel is a first-path stateful delta so candidate ranking stays efficient.\n- Recompute PixelStrokeEngine's scheduler diagnostic ETA from the final ordered base sequence instead of a separate manual accumulator.\n- Preserve `adaptive_hybrid_cost=Off` as the deterministic legacy geometry fallback.\n'''
Path('RELEASE-NOTES-v1.0.145-rc20.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc20 — Pixel Accurate Unified Execution Cost\n\n- Pixel Accurate local orientation and component order now use the same stateful execution-cost model as Extra Fast, Region Fill and visible ETA.\n- Exact coverage and correction behavior are unchanged.\n- Legacy cost-aware planning can still be disabled explicitly.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
import numpy as np
from PIL import Image,ImageDraw

from PixelAccuratePlanner import build_pixel_map
from PixelStrokeEngine import build_pixel_stroke_plan
from PixelAccuracyEngine import simulate_strokes
from ExecutionCostModel import build_cost_model
from Version import APP_VERSION

PALETTE=((255,255,255),(0,0,0),(255,0,0),(0,0,255))


def opts(**kw):
    out={'profile_key':'microsoft-paint','profile_name':'Microsoft Paint','speed':'Balanced',
         'precision':'High','brush_px':1,'delay':.006,'paint_tool':'Pencil',
         'effective_paint_tool':'Pencil','custom_color_workflow':'calibrated-palette',
         'paint_current_color':False,'adaptive_hybrid_cost':'Auto',
         '_hybrid_scale_x':4.0,'_hybrid_scale_y':3.0}
    out.update(kw);return out


class Rc20PixelExecutionCostTests(unittest.TestCase):
    def image(self):
        im=Image.new('RGBA',(32,24),'white');d=ImageDraw.Draw(im)
        d.rectangle((2,3,22,14),fill='red');d.line((27,2,27,20),fill='blue',width=1)
        d.rectangle((8,7,10,9),fill='white')
        return im

    def test_pixel_plan_reports_shared_execution_model_and_scale(self):
        im=self.image();pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts())
        meta=plan['metadata'];self.assertTrue(meta['cost_aware'])
        self.assertEqual(meta['cost_policy'],'ExecutionCostModel stateful v3')
        self.assertEqual(meta['cost_model']['model'],'ExecutionCostModel')
        self.assertAlmostEqual(meta['cost_model']['scale_x'],4.0);self.assertAlmostEqual(meta['cost_model']['scale_y'],3.0)

    def test_scheduler_eta_matches_final_base_sequence_cost(self):
        im=self.image();pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts())
        model=build_cost_model(opts(),pm.width and (pm.width,pm.height),(pm.width,pm.height))
        expected=model.sequence_cost(plan['execution_sequence'],initial_brush=1).total_seconds
        self.assertAlmostEqual(plan['metadata']['estimated_execution_seconds'],round(expected,4),places=4)

    def test_shared_cost_never_breaks_exact_brush1_coverage(self):
        im=self.image();pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts())
        result=simulate_strokes(pm,plan['execution_sequence'],PALETTE,brush_px=1,gpu_mode='CPU')
        target=np.asarray(pm.drawable_mask,dtype=bool)
        self.assertTrue(np.array_equal(result.covered_mask,target))
        self.assertEqual(int(result.error_pixels),0)

    def test_cost_model_off_keeps_legacy_fallback(self):
        im=self.image();pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts(adaptive_hybrid_cost='Off'))
        self.assertFalse(plan['metadata']['cost_aware'])
        self.assertEqual(plan['metadata']['cost_policy'],'legacy geometry scheduler')

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc20')


if __name__=='__main__':unittest.main()
''')
Path('test_rc20_pixel_execution_cost.py').write_text(TEST,encoding='utf-8')
