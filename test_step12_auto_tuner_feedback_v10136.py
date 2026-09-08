import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

import AutoTunerFeedback
from AutoTunerFeedback import record_completed_feedback, recommend_adjustment, reset_profile
from EndToEndAutoTuner import tune_options
from ProfileStorage import profile_auto_tuner_feedback_file


def base_options(seconds=80, profile='Gartic Phone'):
    key={'Gartic Phone':'gartic-phone','Microsoft Paint':'microsoft-paint','Skribbl.io':'skribbl'}.get(profile,'generic')
    return {
        'render_preset':'Auto','profile_name':profile,'profile_key':key,
        'color_fidelity':'Faithful','fill_tool_available':True,'exact_color_available':True,
        'time_budget_mode':'Manual','time_budget_active':True,'time_budget_seconds':seconds,
        'max_seconds':seconds,'manual_max_seconds':seconds,'deadline_render_budget_seconds':float(seconds),
        'deadline_total_seconds':float(seconds),'deadline_safety_reserve_seconds':0.0,
        'outline':False,'erase_mode':False,'paint_current_color':False,
        'paint_tool':'Brush','brush_px':1,'custom_color_workflow':'Adaptive exact (recommended)',
    }


def flat_image():
    im=Image.new('RGB',(120,80),'white'); d=ImageDraw.Draw(im)
    d.rounded_rectangle((10,10,110,70),radius=12,fill=(242,205,31),outline=(60,45,12),width=3)
    d.rectangle((70,25,104,58),fill=(50,150,82))
    return im


def plan_for(options, *, strategy='deadline-hybrid-fast', source_kind='flat illustration', predicted=50.0,
             visual=82.0, usable=80.0, count=100, runtime_meta=None, post_draw=None):
    opts=dict(options)
    opts['auto_tuner_meta']={
        'active':True,'selected_strategy':strategy,'source_features':{'source_kind':source_kind},
        'acceptance_gates':{'visual_accuracy_min_percent':76.0,'usable_deadline_seconds':usable},
    }
    opts['auto_tuner_acceptance_meta']={
        'usable_deadline_seconds':usable,
        'gates':{'visual_accuracy_min_percent':76.0,'usable_deadline_seconds':usable},
    }
    opts['adaptive_accuracy_meta']={
        'visual_accuracy_percent':visual,'perceptual_color_accuracy_percent':80.0,
        'edge_accuracy_percent':80.0,'coverage_percent':100.0,'plan_execution_accuracy_percent':100.0,
    }
    if runtime_meta:
        opts['deadline_runtime_meta']=dict(runtime_meta)
    if post_draw:
        opts['post_draw_accuracy_meta']=dict(post_draw)
    return {'options':opts,'estimate':predicted,'draw_time_estimate':{'projected_seconds':predicted},
            'count':count,'raw_execution_estimate_seconds':predicted,'plan_area':(120,80)}


class Step12AutoTunerFeedbackTests(unittest.TestCase):
    def test_completed_real_draw_records_bounded_profile_local_metrics_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'feedback.json'
            plan=plan_for(base_options(), predicted=50.0, visual=84.0, usable=80.0, count=120)
            result=record_completed_feedback(plan, 46.0, completed_paths=120, path=path)
            self.assertTrue(result['recorded'])
            self.assertEqual(result['profile_key'],'gartic-phone')
            raw=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(raw['profile_key'],'gartic-phone')
            item=next(iter(raw['contexts'].values()))
            self.assertEqual(item['samples'],1)
            self.assertIn('time_ratio_ema',item)
            payload=json.dumps(raw).lower()
            self.assertNotIn('image_data',payload)
            self.assertNotIn('pixels',payload)
            self.assertNotIn('screenshot',payload)

    def test_dry_run_test_and_resume_samples_are_not_learned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'feedback.json'
            for key in ('test_run','dry_run_sampled','render_resume_state'):
                options=base_options(); options[key]=True
                result=record_completed_feedback(plan_for(options), 50.0, completed_paths=100, path=path)
                self.assertFalse(result['recorded'])
            self.assertFalse(path.exists())

    def test_slow_deadline_history_recommends_deadline_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'feedback.json'
            options=base_options(80)
            for _ in range(3):
                plan=plan_for(options, predicted=50.0, usable=60.0, visual=85.0, count=100)
                result=record_completed_feedback(plan, 70.0, completed_paths=100, path=path)
                self.assertTrue(result['recorded'])
            rec=recommend_adjustment(options, source_kind='flat illustration', strategy='deadline-hybrid-fast',
                                     budget_seconds=60.0, color_ceiling=14, visual_gate_percent=76.0, path=path)
            self.assertTrue(rec['active'])
            self.assertEqual(rec['action'],'protect-deadline')
            self.assertTrue(rec['changes']['extra_fast_v2'])
            self.assertLess(rec['color_ceiling_after'], rec['color_ceiling_before'])

    def test_fast_low_quality_history_can_buy_quality_with_headroom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'feedback.json'
            options=base_options(150)
            for _ in range(3):
                plan=plan_for(options, predicted=100.0, usable=150.0, visual=69.0, count=100,
                              post_draw={'visual_accuracy_percent':69.0,'feedback_trust':'high'})
                result=record_completed_feedback(plan, 70.0, completed_paths=100, path=path)
                self.assertTrue(result['recorded'])
            rec=recommend_adjustment(options, source_kind='flat illustration', strategy='deadline-hybrid-fast',
                                     budget_seconds=150.0, color_ceiling=12, visual_gate_percent=76.0, path=path)
            self.assertTrue(rec['active'])
            self.assertEqual(rec['action'],'buy-quality')
            self.assertGreater(rec['color_ceiling_after'], rec['color_ceiling_before'])
            self.assertEqual(rec['changes']['precision'],'High')

    def test_profile_default_files_are_separate(self):
        paint=profile_auto_tuner_feedback_file('microsoft-paint')
        gartic=profile_auto_tuner_feedback_file('gartic-phone')
        skribbl=profile_auto_tuner_feedback_file('skribbl')
        self.assertNotEqual(paint.name, gartic.name)
        self.assertNotEqual(gartic.name, skribbl.name)
        self.assertIn('microsoft-paint',paint.name)

    def test_reset_profile_deletes_only_that_feedback_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'feedback.json'
            result=record_completed_feedback(plan_for(base_options()), 45.0, completed_paths=100, path=path)
            self.assertTrue(result['recorded'])
            self.assertTrue(path.exists())
            reset=reset_profile(base_options(), path=path)
            self.assertTrue(reset['reset'])
            self.assertFalse(path.exists())

    def test_tune_options_applies_learned_feedback_without_touching_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'feedback-gartic-phone.json'
            options=base_options(80)
            original_resolver=AutoTunerFeedback.profile_auto_tuner_feedback_file
            try:
                AutoTunerFeedback.profile_auto_tuner_feedback_file=lambda profile_key: path
                probe=tune_options(flat_image(), options, source_kind_hint='photo / texture')
                probe_meta=probe['auto_tuner_meta']
                strategy=probe_meta['base_strategy']
                source_kind=probe_meta['source_features']['source_kind']
                for _ in range(3):
                    result=record_completed_feedback(
                        plan_for(options, strategy=strategy, source_kind=source_kind,
                                 predicted=50.0, usable=80.0, visual=83.0),
                        70.0, completed_paths=100, path=path)
                    self.assertTrue(result['recorded'])
                tuned=tune_options(flat_image(), options, source_kind_hint='photo / texture')
            finally:
                AutoTunerFeedback.profile_auto_tuner_feedback_file=original_resolver
            feedback=tuned['auto_tuner_meta']['feedback_learning']
            self.assertEqual(feedback['state'],'learned')
            self.assertIn(feedback['action'],('protect-deadline','none'))
            self.assertIn('feedback_learning', tuned['auto_tuner_meta'])
            self.assertNotIn('_accuracy_original_source', feedback)

    def test_release_build_collects_step12_module_and_doc(self):
        source=Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'AutoTunerFeedback'",source)
        self.assertIn('STEP-12-AUTO-TUNER-FEEDBACK-LOOP.md',source)
        self.assertTrue(Path('STEP-12-AUTO-TUNER-FEEDBACK-LOOP.md').is_file())


if __name__=='__main__':
    unittest.main()
