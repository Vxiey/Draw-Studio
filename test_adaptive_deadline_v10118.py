import unittest
import numpy as np
from PIL import Image, ImageDraw

from TimeBudgetEngine import resolve_budget, classify_budget
from VisualImportanceMap import build_importance_map
from AdaptiveDeadlineRenderer import adapt_execution_plan
from DeadlineScheduler import DeadlineScheduler
from AccuracyEvaluator import evaluate_preview


class AdaptiveDeadlineV10118Tests(unittest.TestCase):
    def test_game_presets_keep_real_safety_reserve(self):
        g = resolve_budget('Gartic Phone Fast', 180, 'Auto')
        self.assertEqual(g['total_seconds'], 75.0)
        self.assertEqual(g['reserve_seconds'], 8.0)
        self.assertEqual(g['render_budget_seconds'], 67.0)
        s = resolve_budget('Skribbl Default', 180, 'Auto')
        self.assertEqual(s['total_seconds'], 80.0)
        self.assertEqual(s['render_budget_seconds'], 72.0)
        self.assertEqual(classify_budget(69, 72), 'CLOSE')

    def test_custom_deadline_has_configurable_reserve(self):
        meta = resolve_budget('Custom', 100, '15')
        self.assertEqual(meta['total_seconds'], 100.0)
        self.assertEqual(meta['reserve_seconds'], 15.0)
        self.assertEqual(meta['render_budget_seconds'], 85.0)

    def test_importance_protects_small_high_contrast_feature(self):
        im = Image.new('RGB', (64, 64), (180, 180, 180))
        d = ImageDraw.Draw(im)
        d.rectangle((30, 30, 32, 32), fill=(0, 0, 0))
        importance, meta = build_importance_map(im, {'gpu_mode': 'CPU'})
        self.assertEqual(importance.shape, (64, 64))
        self.assertGreater(float(importance[30:33,30:33].mean()), float(importance[5:15,5:15].mean()) + .2)
        self.assertEqual(meta['backend'], 'cpu-numpy')

    def test_tight_budget_drops_low_value_paths_but_keeps_structure(self):
        im = Image.new('RGB', (96, 96), 'white')
        d = ImageDraw.Draw(im)
        d.rectangle((8, 8, 87, 87), outline='black', width=2)
        groups = [[] for _ in range(2)]
        # One large silhouette plus enough low-value dots to exceed a tight plan.
        groups[0].append(((8,8),(87,8),(87,87),(8,87),(8,8)))
        for i in range(2600):
            groups[1].append(((i % 96, (i * 17) % 96),))
        options = {
            'time_budget_mode':'Emergency 30 s','manual_max_seconds':30,'deadline_safety_reserve':'Auto',
            'adaptive_deadline_renderer':True,'speed':'Balanced','delay':.006,'precision':'High',
            'profile_key':'skribbl','paint_profile':False,'stroke_step_px':8,'paint_current_color':False,
            'fill_regions':[],'tool_actions':[],'color_selectors':[],
        }
        filtered, seq, meta, importance = adapt_execution_plan(im, (960,960), groups, options)
        self.assertTrue(meta['enabled'])
        self.assertGreater(meta['dropped_paths'], 0)
        self.assertLess(meta['selected_paths'], meta['source_paths'])
        self.assertTrue(any(len(e['path']) >= 4 for e in seq))
        self.assertIn(meta['budget_status'], ('SAFE','CLOSE'))
        self.assertIsNotNone(importance)

    def test_runtime_scheduler_enters_panic_and_skips_optional(self):
        now = [0.0]
        seq = [
            {'estimated_cost_seconds':4.0,'phase':'major_coverage','deadline_phase':'major_coverage','importance':.8,'optional':False},
            {'estimated_cost_seconds':8.0,'phase':'correction','deadline_phase':'correction','importance':.2,'optional':True},
        ]
        sched = DeadlineScheduler(seq, start_time=0.0, budget_seconds=5.0, clock=lambda: now[0])
        d1 = sched.before(seq[0])
        self.assertTrue(d1.execute)
        sched.after(seq[0])
        now[0] = 4.2
        d2 = sched.before(seq[1])
        self.assertFalse(d2.execute)
        self.assertTrue(d2.panic)

    def test_accuracy_evaluator_prefers_exact_preview(self):
        src = Image.new('RGB',(32,32),(30,90,180))
        exact = evaluate_preview(src, src.copy())
        wrong = evaluate_preview(src, Image.new('RGB',(32,32),'white'))
        self.assertGreater(exact['visual_accuracy_percent'], 99.9)
        self.assertGreater(exact['raw_pixel_accuracy_percent'], wrong['raw_pixel_accuracy_percent'])

if __name__ == '__main__':
    unittest.main()
