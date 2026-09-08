import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from EndToEndAutoTuner import (tune_options, evaluate_plan_acceptance,
                               propose_rescue_options, acceptance_gates)


def flat_image():
    im=Image.new('RGB',(120,80),'white'); d=ImageDraw.Draw(im)
    d.rounded_rectangle((10,10,110,70),radius=14,fill=(244,204,35),outline=(55,45,20),width=3)
    d.rectangle((72,28,103,55),fill=(42,155,80))
    return im


def texture_image():
    im=Image.new('RGB',(120,80),'white'); px=im.load()
    for y in range(80):
        for x in range(120):
            px[x,y]=((x*7+y*3)%256,(x*3+y*11)%256,(x*13+y*5)%256)
    return im


def base_options(seconds=None, profile='Gartic Phone'):
    key={'Gartic Phone':'gartic-phone','Microsoft Paint':'microsoft-paint','Skribbl.io':'skribbl'}.get(profile,'generic')
    o={'render_preset':'Auto','profile_name':profile,'profile_key':key,'color_fidelity':'Faithful',
       'fill_tool_available':True,'exact_color_available':True,'time_budget_mode':'Manual','max_seconds':180,
       'manual_max_seconds':180,'time_budget_active':False,'outline':False,'erase_mode':False,'paint_current_color':False}
    if seconds is not None:
        o.update(time_budget_active=True,time_budget_seconds=seconds,max_seconds=seconds,
                 deadline_render_budget_seconds=float(seconds),deadline_total_seconds=float(seconds),
                 deadline_safety_reserve_seconds=0.0)
    return o


class Step11EndToEndAutoTunerTests(unittest.TestCase):
    def test_75_and_80_second_class_select_deadline_hybrid(self):
        for seconds in (75,80):
            out=tune_options(texture_image(),base_options(seconds))
            meta=out['auto_tuner_meta']
            self.assertEqual(meta['selected_strategy'],'deadline-hybrid-fast')
            self.assertEqual(out['speed'],'Fast')
            self.assertTrue(out['extra_fast_v2'])
            self.assertEqual(out['planning_resolution'],'Standard')
            self.assertLessEqual(out['exact_color_limit_profile_ceiling'],14)
            self.assertEqual(out['exact_color_limit'],'Auto')

    def test_more_time_never_reduces_tuner_color_ceiling(self):
        values=[]
        for seconds in (75,80,150,300):
            values.append(tune_options(texture_image(),base_options(seconds))['exact_color_limit_profile_ceiling'])
        self.assertEqual(values,sorted(values))
        self.assertGreater(values[-1],values[0])

    def test_flat_source_uses_shape_quality_when_budget_allows(self):
        out=tune_options(flat_image(),base_options(150))
        self.assertIn(out['auto_tuner_meta']['selected_strategy'],('shape-balanced','hybrid-balanced'))
        if out['auto_tuner_meta']['selected_strategy']=='shape-balanced':
            self.assertEqual(out['drawing_mode'],'Shape paths')
            self.assertFalse(out['extra_fast_v2'])

    def test_no_deadline_prefers_quality_over_short_budget_policy(self):
        out=tune_options(flat_image(),base_options(None))
        self.assertIn(out['draw_quality'],('Maximum likeness','Pixel Accurate'))
        self.assertEqual(out['speed'],'Balanced')
        self.assertGreaterEqual(out['exact_color_limit_profile_ceiling'],16)

    def test_paint_has_stricter_visual_acceptance_gate(self):
        paint=acceptance_gates(base_options(80,'Microsoft Paint'))
        browser=acceptance_gates(base_options(80,'Gartic Phone'))
        self.assertGreater(paint['visual_accuracy_min_percent'],browser['visual_accuracy_min_percent'])

    def test_plan_execution_100_cannot_hide_source_accuracy_failure(self):
        options=tune_options(flat_image(),base_options(80))
        options['adaptive_accuracy_meta']={
            'visual_accuracy_percent':61.0,'perceptual_color_accuracy_percent':55.0,
            'edge_accuracy_percent':90.0,'coverage_percent':100.0,'plan_execution_accuracy_percent':100.0}
        plan={'options':options,'estimate':60.0,'draw_time_estimate':{'projected_seconds':60.0},'count':500}
        result=evaluate_plan_acceptance(plan)
        self.assertEqual(result['status'],'BELOW_QUALITY_GATE')
        self.assertFalse(result['accepted'])
        self.assertTrue(result['checks']['plan_execution'])
        self.assertFalse(result['checks']['visual'])

    def test_visual_gate_tolerates_sub_tenth_percent_rounding_jitter(self):
        options=tune_options(flat_image(),base_options(300))
        gate=options['auto_tuner_meta']['acceptance_gates']['visual_accuracy_min_percent']
        options['adaptive_accuracy_meta']={
            'visual_accuracy_percent':gate-0.03,'perceptual_color_accuracy_percent':95.0,
            'edge_accuracy_percent':95.0,'coverage_percent':100.0,'plan_execution_accuracy_percent':100.0}
        plan={'options':options,'estimate':60.0,'draw_time_estimate':{'projected_seconds':60.0},'count':500}
        result=evaluate_plan_acceptance(plan)
        self.assertTrue(result['checks']['visual'])
        self.assertTrue(result['accepted'])

    def test_deadline_gate_rejects_over_budget_plan(self):
        options=tune_options(flat_image(),base_options(80))
        options['adaptive_accuracy_meta']={
            'visual_accuracy_percent':95.0,'perceptual_color_accuracy_percent':95.0,
            'edge_accuracy_percent':95.0,'coverage_percent':100.0,'plan_execution_accuracy_percent':100.0}
        plan={'options':options,'estimate':92.0,'draw_time_estimate':{'projected_seconds':92.0},'count':500}
        result=evaluate_plan_acceptance(plan)
        self.assertEqual(result['status'],'OVER_BUDGET')
        self.assertFalse(result['deadline_gate_passed'])

    def test_deadline_rescue_is_bounded_and_faster(self):
        options=tune_options(texture_image(),base_options(80))
        options['adaptive_accuracy_meta']={
            'visual_accuracy_percent':82.0,'perceptual_color_accuracy_percent':80.0,
            'edge_accuracy_percent':82.0,'coverage_percent':100.0,'plan_execution_accuracy_percent':100.0}
        plan={'options':options,'estimate':100.0,'draw_time_estimate':{'projected_seconds':100.0},
              'performance_profile':{'total_planning':1.0},'count':1200}
        acc=evaluate_plan_acceptance(plan)
        rescue=propose_rescue_options(plan,acc)
        self.assertIsNotNone(rescue)
        self.assertEqual(rescue['auto_tuner_meta']['selected_strategy'],'deadline-rescue')
        self.assertEqual(rescue['speed'],'Fast')
        self.assertTrue(rescue['extra_fast_v2'])
        self.assertLessEqual(rescue['exact_color_limit_profile_ceiling'],options['exact_color_limit_profile_ceiling'])
        rescue['_auto_tuner_replan_attempt']=1
        self.assertIsNone(propose_rescue_options({'options':rescue,'draw_time_estimate':{'projected_seconds':100}},acc))

    def test_quality_rescue_only_spends_real_headroom(self):
        options=tune_options(texture_image(),base_options(150))
        options['adaptive_accuracy_meta']={
            'visual_accuracy_percent':65.0,'perceptual_color_accuracy_percent':60.0,
            'edge_accuracy_percent':80.0,'coverage_percent':100.0,'plan_execution_accuracy_percent':100.0}
        plan={'options':options,'estimate':80.0,'draw_time_estimate':{'projected_seconds':80.0},
              'performance_profile':{'total_planning':1.0},'count':600}
        acc=evaluate_plan_acceptance(plan)
        rescue=propose_rescue_options(plan,acc)
        self.assertIsNotNone(rescue)
        self.assertEqual(rescue['auto_tuner_meta']['selected_strategy'],'quality-rescue')
        self.assertGreaterEqual(rescue['exact_color_limit_profile_ceiling'],options['exact_color_limit_profile_ceiling'])

    def test_auto_drawing_keeps_legacy_engine_labels(self):
        from AutoDrawing import resolve_drawing
        out=resolve_drawing(flat_image(),base_options(None))
        self.assertEqual(out['auto_drawing_meta']['engine'],'Shape paths')
        self.assertTrue(out['auto_drawing_meta']['step11_auto_tuner'])

    def test_small_make_plan_exposes_tuner_and_acceptance_metadata(self):
        from DrawBot import make_plan
        from test_pixel_accurate_v1086 import opts
        o=opts(render_preset='Auto',draw_quality='High likeness',planning_resolution='Standard',
               custom_color_workflow='Adaptive exact (recommended)',exact_color_available=True,
               exact_color_limit='Auto',profile_name='Gartic Phone',profile_key='gartic-phone',paint_profile=False,
               time_budget_mode='Manual',time_budget_active=True,max_seconds=80,manual_max_seconds=80,
               deadline_render_budget_seconds=80,deadline_total_seconds=80,deadline_safety_reserve_seconds=0,
               fill_tool_available=False,resource_scheduler='Off')
        plan=make_plan(flat_image().resize((48,32)),(96,64),o)
        self.assertTrue(plan['options']['auto_tuner_meta']['active'])
        self.assertIn('auto_tuner_acceptance_meta',plan['options'])
        self.assertIn(plan['options']['auto_tuner_acceptance_meta']['status'],
                      ('PASS','OVER_BUDGET','BELOW_QUALITY_GATE','OVER_BUDGET_AND_BELOW_QUALITY','UNVERIFIED'))
        self.assertIn('auto_tuner',plan['preview_diagnostics'])

    def test_release_build_collects_step11_module_and_doc(self):
        source=Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'EndToEndAutoTuner'",source)
        self.assertIn('STEP-11-END-TO-END-AUTO-TUNER.md',source)


if __name__=='__main__':
    unittest.main()
