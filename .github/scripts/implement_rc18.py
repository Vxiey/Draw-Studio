from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc18 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')


# Preserve the old formula as a fallback, but make the shared stateful
# ExecutionCostModel authoritative for Fill-vs-scanline timing decisions.
p=Path('RegionFillEngine.py')
text=p.read_text(encoding='utf-8')
start=text.index('def _region_cost(region:')
end=text.index('\ndef _batchable_tool_cost', start)
old_block=text[start:end]
legacy=old_block.replace('def _region_cost(region:', 'def _legacy_region_cost(region:', 1)
new_block=dedent(r'''
def _region_cost(region: dict[str, Any], options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> tuple[float, float]:
    """Compare connected scanlines with Outline + Fill using shared execution cost.

    Safety is decided elsewhere.  This function only answers the performance
    question with the same stateful cursor/drag/switch model used by Adaptive
    Region Hybrid and the visible ETA.  The pre-rc18 formula remains a bounded
    fallback if the shared model cannot cost an unusual region.
    """
    try:
        from ExecutionCostModel import build_cost_model
        model=build_cost_model(options,image_size,fitted)
        color=max(0,int(region.get("color_index",0) or 0))
        brush=max(1,int(options.get("brush_px",1) or 1))
        stroke_sequence=[]
        for serial,raw in enumerate(region.get("row_spans") or ()):
            try:y,left,right=map(int,raw)
            except Exception:continue
            path=((left,y),) if left==right else ((left,y),(right,y))
            stroke_sequence.append({"color_index":color,"brush_px":brush,"path":path,
                                    "operation_type":"dot" if len(path)==1 else "stroke",
                                    "local_serial":serial})
        stroke_cost=model.sequence_cost(stroke_sequence,initial_color=color,initial_brush=brush).total_seconds

        contour=[]
        for raw in region.get("contour") or ():
            try:contour.append((int(raw[0]),int(raw[1])))
            except Exception:continue
        if contour and len(contour)>1 and contour[0]!=contour[-1]:contour.append(contour[0])
        contour_sequence=[]
        if contour:
            contour_sequence=[{"color_index":color,"brush_px":brush,"path":tuple(contour),
                               "operation_type":"outline"}]
        contour_cost=model.sequence_cost(contour_sequence,initial_color=color,initial_brush=brush).total_seconds
        # One tool switch is deliberately kept batchable, matching the previous
        # RegionFillEngine contract. estimate_fill_execution_seconds removes that
        # per-region share and adds the real calibrated Fill/restore controls once
        # per colour batch.
        fill_cost=(contour_cost+model.switch_cost("tool_change")+
                   model.switch_cost("fill")+model.switch_cost("verification"))
        if stroke_cost>0 and fill_cost>0:
            return max(.001,float(stroke_cost)),max(.001,float(fill_cost))
    except Exception:
        pass
    return _legacy_region_cost(region,options,image_size,fitted)
''')
p.write_text(text[:start]+legacy+'\n'+new_block+text[end:],encoding='utf-8')

# The batchable share must come from the same shared model too. Fallback remains
# the old delivery heuristic when model construction is unavailable.
p=Path('RegionFillEngine.py');text=p.read_text(encoding='utf-8')
start=text.index('def _batchable_tool_cost(')
end=text.index('\ndef _region_cost_components',start)
new_batch=dedent(r'''
def _batchable_tool_cost(options: dict[str, Any]) -> float:
    """Per-region tool-switch share already embedded in the Fill candidate cost."""
    try:
        from ExecutionCostModel import build_cost_model
        # Switch cost is independent of geometry; 1x1 keeps this helper cheap.
        model=build_cost_model(options,(1,1),(1,1))
        return max(0.0,float(model.switch_cost("tool_change")))
    except Exception:
        delivery=resolve_stroke_delivery(options,dry_run=False)
        return max(.08,float(delivery.ui_control_delay)*.45)
''')
p.write_text(text[:start]+new_batch+text[end:],encoding='utf-8')

# Surface which cost policy made the decisions in plan metadata.
replace('RegionFillEngine.py',
'''        'fallback_render_method':'CONNECTED_SCANLINES','extra_fast_batch_aware_costing':bool(options.get('extra_fast')),\n''',
'''        'fallback_render_method':'CONNECTED_SCANLINES','extra_fast_batch_aware_costing':bool(options.get('extra_fast')),\n        'execution_cost_model':'ExecutionCostModel stateful v2','execution_cost_fallback':'legacy RegionFill formula on model error',\n''')

# Version / release surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc17'","APP_VERSION = '1.0.145-rc18'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc17"','#define MyAppVersion "1.0.145-rc18"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc17' in raw:test.write_text(raw.replace('1.0.145-rc17','1.0.145-rc18'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc17','1.0.145-rc18'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc18 — Unified Region Fill Cost\n\n- Make Region Fill compare connected scanlines against Outline + Fill with the shared stateful `ExecutionCostModel`.\n- Include real ordered scanline cursor travel, sampled drag cost and the configured Fill/tool/verification switch cost in Fill decisions.\n- Keep the existing Region Fill safety gates unchanged: leak prediction, thin-neck blockers, source masks, diagonal pre-seals and runtime flood verification remain authoritative.\n- Keep the previous Region Fill timing formula only as a safe fallback if the shared execution model cannot cost an unusual region.\n- Use the same execution-model tool-switch cost when batching same-colour Fill regions so per-region tool overhead is removed consistently.\n- Export the active Fill cost policy in Region Fill metadata for diagnostics.\n'''
Path('RELEASE-NOTES-v1.0.145-rc18.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc18 — Unified Region Fill Cost\n\n- Fill-vs-stroke decisions now use the same stateful ExecutionCostModel as Adaptive Hybrid and Estimated Draw Time.\n- Fill safety logic is unchanged; only execution-time comparison is unified.\n- Legacy Fill costing remains fallback-only.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from unittest import mock
from types import SimpleNamespace

from RegionFillEngine import _batchable_tool_cost, _region_cost, evaluate_region_candidates
from Version import APP_VERSION


class FakeModel:
    def __init__(self):self.calls=[]
    def sequence_cost(self,sequence,**kwargs):
        seq=list(sequence);self.calls.append((seq,kwargs))
        # Scanlines contain several entries; one contour is intentionally cheaper.
        return SimpleNamespace(total_seconds=2.0*len(seq) if len(seq)>1 else 1.25)
    def switch_cost(self,kind):
        return {'tool_change':.30,'fill':.20,'verification':.10}.get(kind,.05)


def region():
    return {'color_index':2,'row_spans':[(y,2,10) for y in range(6)],
            'contour':[(2,0),(10,0),(10,5),(2,5),(2,0)],'seed_pixel':(5,2),
            'guard_pixels':[(0,2),(12,2)],'area_pixels':54,'safety_score':.99,
            'bbox_density':1.0,'perimeter_pixels':28}


class Rc18UnifiedRegionFillCostTests(unittest.TestCase):
    def test_region_cost_uses_shared_execution_model(self):
        fake=FakeModel()
        with mock.patch('ExecutionCostModel.build_cost_model',return_value=fake):
            stroke,fill=_region_cost(region(),{'brush_px':4},(20,20),(200,200))
        self.assertAlmostEqual(stroke,12.0);self.assertAlmostEqual(fill,1.85)
        self.assertEqual(fake.calls[0][1]['initial_color'],2)
        self.assertEqual(fake.calls[0][1]['initial_brush'],4)

    def test_batchable_tool_cost_uses_same_model(self):
        with mock.patch('ExecutionCostModel.build_cost_model',return_value=FakeModel()):
            self.assertAlmostEqual(_batchable_tool_cost({'brush_px':2}),.30)

    def test_cost_model_failure_falls_back_without_disabling_fill_engine(self):
        opts={'speed':'Balanced','delay':.003,'brush_px':2}
        with mock.patch('ExecutionCostModel.build_cost_model',side_effect=RuntimeError('no model')):
            stroke,fill=_region_cost(region(),opts,(20,20),(200,200))
        self.assertGreater(stroke,0);self.assertGreater(fill,0)

    def test_safety_gate_still_rejects_thin_neck_before_cost_wins(self):
        thin={'color_index':1,'row_spans':[(y,5,5) for y in range(8)],
              'contour':[(5,0),(5,1),(5,7),(5,6),(5,0)],'seed_pixel':(5,3),
              'guard_pixels':[(3,3),(7,3)],'area_pixels':8,'safety_score':.99,
              'bbox_density':1.0,'perimeter_pixels':16}
        accepted,meta=evaluate_region_candidates([thin],(20,20),(200,200),
            {'speed':'Fast','brush_px':4,'fill_aggressiveness':'Aggressive','fill_tool_available':True})
        self.assertEqual(accepted,[]);self.assertGreaterEqual(meta['rejected_by_safety'],1)

    def test_metadata_reports_shared_cost_policy(self):
        accepted,meta=evaluate_region_candidates([region()],(20,20),(200,200),
            {'speed':'Fast','brush_px':2,'fill_aggressiveness':'Balanced','fill_tool_available':True})
        self.assertEqual(meta['execution_cost_model'],'ExecutionCostModel stateful v2')

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc18')


if __name__=='__main__':unittest.main()
''')
Path('test_rc18_unified_region_fill_cost.py').write_text(TEST,encoding='utf-8')
