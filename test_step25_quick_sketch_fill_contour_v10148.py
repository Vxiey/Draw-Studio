import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from QuickSketchFillContour import (
    QUICK_SKETCH_RENDER_STYLE, QUICK_SKETCH_STYLES, QUICK_SKETCH_FILL_PREFERENCES,
    apply_quick_sketch_policy, build_quick_sketch_geometry, resolve_color_cap,
)
from EndToEndAutoTuner import tune_options


class Step25QuickSketchFillContourTests(unittest.TestCase):
    @staticmethod
    def opts(**extra):
        out = {
            'render_style': QUICK_SKETCH_RENDER_STYLE,
            'quick_sketch_style': 'Balanced',
            'quick_sketch_fill_preference': 'Safe Fill First',
            'fill_tool_available': True, 'use_region_fill_engine': True,
            'draw_quality': 'High likeness', 'brush_px': 1, 'delay': .003,
            'speed': 'Fast', 'precision': 'Normal',
            'time_budget_active': True, 'time_budget_seconds': 80, 'max_seconds': 80,
            'fill_tool_actions': [('fill',(1,1))], 'fill_restore_actions': [('brush',(2,2))],
            'profile_key': 'gartic-phone', 'profile_name': 'Gartic Phone',
            'color_fidelity': 'Faithful', 'safe_fill_mask_margin_px': 0,
            'detail_zoom': 'Auto', 'canvas_guard_enabled': True,
        }
        out.update(extra)
        return out

    @staticmethod
    def rectangle_groups():
        groups = [[], [(12,y,45,y) for y in range(10,36)], [], []]
        palette = ((255,255,255),(220,40,30),(30,30,30),(240,210,40))
        return groups, palette

    def test_policy_is_recognition_first_but_does_not_weaken_safety(self):
        source = self.opts(canvas_guard_enabled=True, strict_runtime_safety=True,
                           fill_tool_available=True, safe_fill_mask_margin_px=2)
        out = apply_quick_sketch_policy(source)
        self.assertTrue(out['quick_sketch_enabled'])
        self.assertEqual(out['drawing_mode'], 'Smart paths (recommended)')
        self.assertEqual(out['fill_engine'], 'Closed regions v2')
        self.assertEqual(out['shape_order'], 'Fill first')
        self.assertTrue(out['use_region_fill_engine'])
        self.assertEqual(out['background_fill'], 'Off')
        self.assertTrue(out['canvas_guard_enabled'])
        self.assertTrue(out['strict_runtime_safety'])
        self.assertEqual(out['safe_fill_mask_margin_px'], 2)

    def test_color_budget_is_style_and_deadline_aware(self):
        self.assertEqual(QUICK_SKETCH_STYLES, ('Simple','Balanced','Detailed'))
        self.assertEqual(QUICK_SKETCH_FILL_PREFERENCES, ('Safe Fill First','Balanced','Scanline Preferred'))
        short = resolve_color_cap(self.opts(quick_sketch_style='Simple', time_budget_seconds=80))
        detailed = resolve_color_cap(self.opts(quick_sketch_style='Detailed', time_budget_seconds=80))
        unlimited = resolve_color_cap(self.opts(quick_sketch_style='Balanced', time_budget_active=False))
        self.assertLess(short, detailed)
        self.assertGreater(unlimited, short)

    def test_large_closed_region_becomes_real_safe_fill_plus_visible_contour(self):
        groups, palette = self.rectangle_groups()
        out_groups, fills, meta = build_quick_sketch_geometry(
            (64,48), groups, palette, (640,480), self.opts())
        self.assertGreaterEqual(len(fills), 1)
        self.assertGreater(meta['fill_coverage_percent'], 20.0)
        self.assertGreater(meta['visible_contour_segments'], 0)
        self.assertGreater(meta['filled_source_runs_removed'], 0)
        self.assertGreater(meta['stroke_run_reduction_percent'], 50.0)
        self.assertTrue(all(r.get('render_method') == 'OUTLINE_FILL' for r in fills))
        self.assertIn('Safe Fill Mask', meta['safety_policy'])
        # The 26 scanlines are removed; a compact dark visible contour remains.
        self.assertLess(sum(len(g) for g in out_groups), sum(len(g) for g in groups))

    def test_unavailable_fill_never_invents_bucket_actions(self):
        groups, palette = self.rectangle_groups()
        out_groups, fills, meta = build_quick_sketch_geometry(
            (64,48), groups, palette, (640,480), self.opts(fill_tool_available=False))
        self.assertEqual(fills, [])
        self.assertFalse(meta['fill_tool_available'])
        self.assertIn('scanline fallback', str(meta['fill_safety'].get('reason','')).lower())
        self.assertEqual(meta['visible_contour_segments'], 0)
        self.assertEqual(sum(len(g) for g in out_groups), sum(len(g) for g in groups))

    def test_micro_texture_is_bounded_but_structural_runs_survive(self):
        palette=((255,255,255),(30,30,30))
        # One structural run + far more isolated dots than the 80-second Simple cap.
        group=[(5,20,55,20)] + [(3+(i%55), 2+(i//55), 3+(i%55), 2+(i//55)) for i in range(180)]
        out, fills, meta=build_quick_sketch_geometry(
            (64,48), [[],group], palette, (640,480),
            self.opts(fill_tool_available=False, quick_sketch_style='Simple'))
        self.assertEqual(fills, [])
        self.assertGreater(meta['micro_strokes_pruned'], 0)
        self.assertIn((5,20,55,20), out[1])

    def test_auto_tuner_selects_quick_sketch_for_short_flat_fill_safe_source(self):
        im=Image.new('RGB',(120,80),'white'); d=ImageDraw.Draw(im)
        d.rounded_rectangle((10,10,110,70),radius=14,fill=(244,204,35),outline=(55,45,20),width=3)
        d.rectangle((72,28,103,55),fill=(42,155,80))
        o={'render_preset':'Auto','profile_name':'Gartic Phone','profile_key':'gartic-phone',
           'color_fidelity':'Faithful','fill_tool_available':True,'exact_color_available':True,
           'time_budget_mode':'Manual','time_budget_active':True,'time_budget_seconds':80,
           'max_seconds':80,'manual_max_seconds':80,'deadline_render_budget_seconds':80.0,
           'deadline_total_seconds':80.0,'deadline_safety_reserve_seconds':0.0,
           'outline':False,'erase_mode':False,'paint_current_color':False}
        out=tune_options(im,o)
        self.assertEqual(out['auto_tuner_meta']['base_strategy'],'quick-sketch-fill-contour')
        self.assertEqual(out['render_style'], QUICK_SKETCH_RENDER_STYLE)
        self.assertTrue(out['quick_sketch_auto'])
        self.assertEqual(out['quick_sketch_fill_preference'],'Safe Fill First')
        self.assertEqual(out['detail_zoom'],'Auto')

    def test_auto_tuner_keeps_texture_heavy_short_source_on_hybrid(self):
        im=Image.new('RGB',(96,64),'white'); px=im.load()
        for y in range(64):
            for x in range(96):
                px[x,y]=((x*7+y*3)%256,(x*3+y*11)%256,(x*13+y*5)%256)
        o={'render_preset':'Auto','profile_name':'Gartic Phone','profile_key':'gartic-phone',
           'color_fidelity':'Faithful','fill_tool_available':True,'exact_color_available':True,
           'time_budget_mode':'Manual','time_budget_active':True,'time_budget_seconds':80,
           'max_seconds':80,'manual_max_seconds':80,'deadline_render_budget_seconds':80.0,
           'deadline_total_seconds':80.0,'deadline_safety_reserve_seconds':0.0,
           'outline':False,'erase_mode':False,'paint_current_color':False}
        out=tune_options(im,o)
        self.assertEqual(out['auto_tuner_meta']['base_strategy'],'deadline-hybrid-fast')


    def test_make_plan_exposes_quick_sketch_fill_and_diagnostics(self):
        from DrawBot import make_plan
        from test_pixel_accurate_v1086 import opts
        im=Image.new('RGB',(96,64),'white'); d=ImageDraw.Draw(im)
        d.rounded_rectangle((8,8,86,55),radius=10,fill=(244,204,35),outline=(50,40,20),width=2)
        d.rectangle((56,23,78,44),fill=(42,155,80))
        o=opts(render_preset='Manual',render_style=QUICK_SKETCH_RENDER_STYLE,
               quick_sketch_style='Balanced',quick_sketch_fill_preference='Safe Fill First',
               draw_quality='High likeness',planning_resolution='Standard',
               custom_color_workflow='Adaptive exact (recommended)',exact_color_available=True,
               exact_color_limit='Auto',profile_name='Gartic Phone',profile_key='gartic-phone',paint_profile=False,
               time_budget_mode='Manual',time_budget_active=False,max_seconds=180,manual_max_seconds=180,
               fill_tool_available=True,fill_tool_actions=[('fill',(5,5))],
               fill_restore_actions=[('brush',(8,5))],resource_scheduler='Off',detail_zoom='Auto')
        plan=make_plan(im,(192,128),o)
        meta=plan['options'].get('quick_sketch_meta') or {}
        self.assertTrue(meta.get('enabled'))
        self.assertGreaterEqual(int(meta.get('fill_regions',0) or 0),1)
        self.assertGreater(int(meta.get('visible_contour_segments',0) or 0),0)
        self.assertEqual(len(plan['options'].get('fill_regions') or []),int(meta.get('fill_regions',0) or 0))
        self.assertIn('quick_sketch',plan.get('preview_diagnostics',{}))

    def test_ui_and_build_hooks_exist(self):
        base=Path(__file__).resolve().parent
        ui=(base/'StudioUI.py').read_text(encoding='utf-8')
        drawbot=(base/'DrawBot.py').read_text(encoding='utf-8')
        self.assertIn('QUICK_SKETCH_RENDER_STYLE', ui)
        self.assertIn("'Quick Sketch style', a.quick_sketch_style", ui)
        self.assertIn('build_quick_sketch_geometry', drawbot)
        self.assertIn('quick_sketch_meta', drawbot)
        build=(base/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'QuickSketchFillContour'", build)


if __name__ == '__main__':
    unittest.main()
