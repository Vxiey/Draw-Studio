import unittest
from pathlib import Path

from TimeAwareColorBudget import apply_time_aware_color_budget


def base_meta(count=20):
    return {
        'active': True,
        'policy': 'image-complexity-v1',
        'recommended_colors': count,
        'minimum_colors': 2,
        'ceiling_colors': 24,
        'complexity_score': .78,
        'color_entropy': .76,
        'edge_density': .30,
        'tone_bins': 4,
        'dominant_hue_families': ('red','yellow','green','blue'),
        'significant_color_buckets': 30,
        'time_budget_applied': False,
    }


def opts(mode='Manual', *, profile='Microsoft Paint', exact=True, seconds=180, calibration=None):
    result = {
        'time_budget_mode': mode,
        'manual_max_seconds': seconds,
        'max_seconds': seconds,
        'deadline_safety_reserve': 'Auto',
        'profile_name': profile,
        'paint_profile': profile == 'Microsoft Paint',
        'exact_color_available': exact,
        'speed': 'Balanced',
        'precision': 'High',
    }
    if calibration is not None:
        result['_time_color_calibration_override'] = calibration
    return result


class Step6TimeAwareColorBudgetTests(unittest.TestCase):
    def test_manual_mode_preserves_step5_recommendation(self):
        count, meta = apply_time_aware_color_budget(20, base_meta(), opts('Manual'))
        self.assertEqual(count, 20)
        self.assertFalse(meta['time_budget_applied'])
        self.assertFalse(meta['color_budget_limited'])

    def test_unlimited_preserves_step5_recommendation(self):
        count, meta = apply_time_aware_color_budget(20, base_meta(), opts('Unlimited / Accuracy'))
        self.assertEqual(count, 20)
        self.assertFalse(meta['time_budget_applied'])

    def test_60_75_80_150_300_are_monotonic(self):
        modes=('Skribbl 60','Gartic Phone Fast','Skribbl Default','Gartic Phone Normal','Gartic Phone Slow')
        values=[]
        for mode in modes:
            value, meta=apply_time_aware_color_budget(24, base_meta(24), opts(mode,profile='Microsoft Paint',exact=True))
            values.append(value)
            self.assertTrue(meta['time_budget_applied'])
        self.assertEqual(values, sorted(values))
        self.assertLess(values[0], values[-1])

    def test_custom_exact_costs_more_than_browser_palette(self):
        paint, pm=apply_time_aware_color_budget(24, base_meta(24), opts('Skribbl Default',profile='Microsoft Paint',exact=True))
        browser, bm=apply_time_aware_color_budget(24, base_meta(24), opts('Skribbl Default',profile='Skribbl.io',exact=False))
        self.assertGreater(pm['direct_color_change_seconds'], bm['direct_color_change_seconds'])
        self.assertLessEqual(paint, browser)

    def test_measured_color_change_replaces_model(self):
        cal={'samples':4,'operation_runtime':{'color_change':{'count':5,'total_seconds':2.0}},'seconds_per_completed_path':.020}
        _, meta=apply_time_aware_color_budget(20, base_meta(), opts('Skribbl Default',calibration=cal))
        self.assertAlmostEqual(meta['direct_color_change_seconds'], .4, places=6)
        self.assertEqual(meta['direct_color_change_source'],'measured color_change')
        self.assertEqual(meta['seconds_per_path_source'],'measured completed paths')

    def test_high_measured_switch_cost_reduces_colour_count(self):
        low={'samples':3,'operation_runtime':{'color_change':{'count':10,'total_seconds':1.0}},'seconds_per_completed_path':.01}
        high={'samples':3,'operation_runtime':{'color_change':{'count':10,'total_seconds':15.0}},'seconds_per_completed_path':.08}
        low_count,_=apply_time_aware_color_budget(24, base_meta(24), opts('Skribbl Default',calibration=low))
        high_count,_=apply_time_aware_color_budget(24, base_meta(24), opts('Skribbl Default',calibration=high))
        self.assertLess(high_count, low_count)

    def test_structural_hue_and_tone_floor_survives_short_budget(self):
        meta=base_meta(24)
        meta['dominant_hue_families']=('red','orange','yellow','green','cyan','blue')
        count, out=apply_time_aware_color_budget(24, meta, opts('Emergency 30 s'))
        self.assertGreaterEqual(count, 8) # six hue families + light/dark structure
        self.assertEqual(count, out['time_color_floor'])

    def test_resolved_deadline_values_are_reused(self):
        o=opts('Custom', seconds=200)
        o.update(time_budget_active=True, deadline_total_seconds=80, deadline_render_budget_seconds=70,
                 deadline_safety_reserve_seconds=10, deadline_budget_source='test resolved budget')
        _, meta=apply_time_aware_color_budget(20, base_meta(), o)
        self.assertEqual(meta['render_budget_seconds'],70)
        self.assertEqual(meta['timer_total_seconds'],80)
        self.assertEqual(meta['time_budget_source'],'test resolved budget')

    def test_make_plan_exposes_time_adjusted_auto_metadata(self):
        from PIL import Image, ImageDraw
        from DrawBot import make_plan
        from test_pixel_accurate_v1086 import opts as base_opts
        im=Image.new('RGB',(96,64),'white'); d=ImageDraw.Draw(im)
        colors=((230,30,30),(245,210,25),(30,180,60),(30,70,220),(180,60,180),(40,170,190))
        for i,color in enumerate(colors):
            x=(i%3)*32; y=(i//3)*32
            d.rectangle((x,y,x+31,y+31),fill=color)
        options=base_opts(draw_quality='High likeness',custom_color_workflow='Adaptive exact (recommended)',
                          exact_color_limit='Auto',exact_color_available=True,time_budget_mode='Skribbl Default',
                          max_seconds=80,manual_max_seconds=80,planning_resolution='Standard',resource_scheduler='Off')
        plan=make_plan(im,(192,128),options)
        out=plan['options']; meta=out['adaptive_color_count_meta']
        self.assertTrue(meta['time_budget_applied'])
        self.assertEqual(out['exact_color_limit_resolved'],meta['recommended_colors'])
        self.assertEqual(out['advanced_color_meta']['adaptive_color_count']['recommended_colors'],meta['recommended_colors'])
        self.assertEqual(meta['render_budget_seconds'],72.0)

    def test_release_build_includes_time_aware_module(self):
        source=(Path(__file__).resolve().parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'TimeAwareColorBudget'",source)

    def test_drawbot_integrates_step6_only_in_auto_branch(self):
        source=(Path(__file__).resolve().parent/'DrawBot.py').read_text(encoding='utf-8')
        auto=source.index("if exact_limit_setting=='Auto':")
        manual=source.index('else:',auto)
        call=source.index('apply_time_aware_color_budget(',auto)
        self.assertLess(call,manual)
        self.assertIn("'time_budget_applied':False",source[manual:manual+700])


if __name__ == '__main__':
    unittest.main()
