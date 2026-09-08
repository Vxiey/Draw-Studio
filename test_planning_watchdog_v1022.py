import unittest

from PlanningWatchdog import (PLANNING_WATCHDOG_MODES, build_planning_attempts,
                              validate_planning_watchdog, watchdog_enabled)
from ContinuousPaths import SHAPE_PATH_MODE


class PlanningWatchdogTests(unittest.TestCase):
    def options(self, **overrides):
        data = {
            'planning_watchdog': 'Auto',
            'planning_timeout_seconds': 75,
            'drawing_mode': SHAPE_PATH_MODE,
            'speed': 'Fast',
            'planning_resolution': 'Ultra',
            'cpu_workers_resolved': 16,
            'cpu_engine': 'Processes',
            'gpu_mode': 'NVIDIA CUDA',
            'gpu_performance': 'Maximum',
            'color_rendering': 'Perceptual match',
            'color_layers': 'Full color mix',
            'background_fill': 'Balanced',
            'background_simplification': 'Off',
            'target_stroke_count': 'Auto',
            'target_stroke_count_resolved': None,
            'max_stroke_cap': 'Unlimited',
        }
        data.update(overrides)
        return data

    def test_modes_are_validated(self):
        self.assertEqual(validate_planning_watchdog('Auto'), 'Auto')
        self.assertIn('On', PLANNING_WATCHDOG_MODES)
        with self.assertRaisesRegex(ValueError, 'Planning watchdog'):
            validate_planning_watchdog('Always')

    def test_auto_enabled_only_for_final_planning(self):
        self.assertTrue(watchdog_enabled('Auto', preview=False, test=False))
        self.assertFalse(watchdog_enabled('Auto', preview=True, test=False))
        self.assertFalse(watchdog_enabled('Auto', preview=False, test=True))
        self.assertTrue(watchdog_enabled('On', preview=True, test=True))
        self.assertFalse(watchdog_enabled('Off'))

    def test_attempts_add_safe_fallbacks(self):
        attempts = build_planning_attempts(self.options())
        self.assertEqual([a.index for a in attempts], [1, 2, 3])
        self.assertEqual(attempts[0].name, 'Primary settings')
        self.assertLessEqual(attempts[0].timeout_seconds, 24)
        self.assertEqual(attempts[1].options['planning_resolution'], 'Standard')
        self.assertEqual(attempts[1].options['cpu_engine'], 'Threads')
        self.assertEqual(attempts[1].options['color_layers'], 'Off')
        self.assertEqual(attempts[1].options['target_stroke_count_resolved'], 1800)
        self.assertEqual(attempts[2].options['gpu_mode'], 'CPU')
        self.assertEqual(attempts[2].options['color_rendering'], 'RGB nearest')
        self.assertEqual(attempts[2].options['background_fill'], 'Off')
        self.assertEqual(attempts[2].options['target_stroke_count_resolved'], 1200)

    def test_off_keeps_single_original_attempt(self):
        attempts = build_planning_attempts(self.options(planning_watchdog='Off'))
        self.assertEqual(len(attempts), 1)
        self.assertFalse(attempts[0].fallback)
        self.assertEqual(attempts[0].options['planning_resolution'], 'Ultra')

    def test_explicit_small_target_is_preserved(self):
        attempts = build_planning_attempts(self.options(target_stroke_count='500', target_stroke_count_resolved=500))
        self.assertEqual(attempts[1].options['target_stroke_count_resolved'], 500)
        self.assertEqual(attempts[2].options['target_stroke_count_resolved'], 500)


if __name__ == '__main__':
    unittest.main()
