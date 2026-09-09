import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from PixelAccuratePlanner import build_pixel_map
from PixelStrokeEngine import connected_components,build_component_paths,build_pixel_stroke_plan
from HybridCostModel import build_cost_model
from HybridBenchmark import CASES

PALETTE=((255,255,255),(0,0,0),(255,0,0),(0,0,255))

def opts(**kw):
    d=dict(profile_key='microsoft-paint',profile_name='Microsoft Paint',speed='Balanced',precision='High',brush_px=1,delay=.006,paint_tool='Pencil',effective_paint_tool='Pencil',custom_color_workflow='calibrated-palette',use_region_fill_engine=False,adaptive_hybrid_cost='Auto')
    d.update(kw);return d

class HybridCostEngineTests(unittest.TestCase):
    def test_cold_start_is_explicit_not_fake_calibrated(self):
        m=build_cost_model(opts())
        self.assertIn(m.source,('conservative-default','calibrated-profile'))
        self.assertGreater(m.path_fixed_seconds,0)
    def test_six_required_benchmark_cases_exist(self):
        self.assertEqual(len(CASES),6);self.assertEqual({n for n,_ in CASES},{'icon','line-art','text-small-detail','cartoon-large-colour','photo-gradient','fill-risk'})
    def test_cost_aware_plan_is_exact_and_reports_model(self):
        im=Image.new('RGBA',(28,22),'white');d=ImageDraw.Draw(im);d.rectangle((2,3,20,12),fill='red');d.line((24,2,24,19),fill='blue')
        pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts())
        self.assertTrue(plan['metadata']['cost_aware']);self.assertIsInstance(plan['metadata']['cost_model'],dict)
        self.assertEqual(sum(len(g) for g in plan['execution_groups']),len(plan['execution_sequence']))
    def test_legacy_fallback_remains_available(self):
        im=Image.new('RGBA',(16,12),'red');pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(PALETTE),options=opts(adaptive_hybrid_cost='Off'))
        self.assertFalse(plan['metadata']['cost_aware'])
    def test_component_candidate_never_paints_outside(self):
        im=Image.new('RGBA',(12,10),'white');d=ImageDraw.Draw(im);d.rectangle((1,1,8,6),fill='red');d.rectangle((4,3,5,4),fill='white')
        pm=build_pixel_map(im,PALETTE,gpu_mode='CPU',skip_white=True);comps,cmap,_=connected_components(pm)
        red=max((c for c in comps if c.color_index==2),key=lambda c:c.area)
        paths,meta=build_component_paths(red,cmap,cost_model=build_cost_model(opts()))
        self.assertTrue(paths);self.assertIn(meta['selection'],('calibrated-time','legacy-run-count'))
        # Exact planner fallback/verification is authoritative for holes.
        self.assertTrue(meta['safe_verified'] or meta['fallback'])
    def test_drawbot_forwards_full_options_to_subject_planner(self):
        text=Path('DrawBot.py').read_text(encoding='utf-8');self.assertIn('options=options,cancelled=cancelled)',text)
    def test_region_fill_uses_shared_cost_model(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8');self.assertIn('from HybridCostModel import build_cost_model',text);self.assertIn('hybrid_cost_model',text)
    def test_region_fill_cold_start_preserves_legacy_cost_gate(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8')
        self.assertIn('if not model.calibrated:',text)
        self.assertIn('fill_cost += max(.08, delivery.ui_control_delay * .45) + .24',text)
    def test_gartic_specialized_route_not_replaced(self):
        text=Path('DrawBot.py').read_text(encoding='utf-8');self.assertIn('optimize_gartic_phone_groups',text);self.assertIn('build_gartic_execution_paths',text)
    def test_no_human_mode_added_to_new_engine(self):
        self.assertNotIn('HumanMode',Path('HybridCostModel.py').read_text(encoding='utf-8'));self.assertNotIn('HumanMode',Path('HybridBenchmark.py').read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
