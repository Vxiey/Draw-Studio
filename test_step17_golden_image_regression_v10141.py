import json
import tempfile
import unittest
from pathlib import Path

from GoldenImageRegression import (
    GOLDEN_CASES,
    ensure_local_golden_images,
    format_result,
    run,
)


def fake_plan_good(image, target_area, options, cancelled=lambda: False):
    if cancelled():
        raise InterruptedError()
    seconds = float(options.get('time_budget_seconds', 80) or 80)
    return {
        'count': 120,
        'estimate': seconds * 0.72,
        'draw_time_estimate': {'projected_seconds': seconds * 0.72},
        'options': {
            'deadline_render_budget_seconds': seconds * 0.9,
            'adaptive_accuracy_meta': {
                'visual_accuracy_percent': 88.0,
                'source_pixel_accuracy_percent': 91.0,
                'perceptual_color_accuracy_percent': 86.0,
                'luminance_accuracy_percent': 94.0,
                'hue_accuracy_percent': 90.0,
                'edge_accuracy_percent': 89.0,
                'coverage_percent': 95.0,
                'plan_execution_accuracy_percent': 100.0,
                'delta_e_oklab': {'mean_delta_e_oklab': 0.055, 'p95_delta_e_oklab': 0.14},
            },
            'preview_delta_e_meta': {'mean_delta_e_oklab': 0.055, 'p95_delta_e_oklab': 0.14},
            'post_draw_correction_meta': {'safe': True},
        },
    }


def fake_plan_yellow_to_pink(image, target_area, options, cancelled=lambda: False):
    plan = fake_plan_good(image, target_area, options, cancelled)
    plan['options']['adaptive_accuracy_meta'].update({
        'visual_accuracy_percent': 61.0,
        'perceptual_color_accuracy_percent': 55.0,
        'hue_accuracy_percent': 42.0,
        'coverage_percent': 98.0,
    })
    plan['options']['preview_delta_e_meta']['p95_delta_e_oklab'] = 0.41
    return plan


class Step17GoldenImageRegressionTests(unittest.TestCase):
    def test_ensure_local_assets_and_manifest_are_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = ensure_local_golden_images(tmp, overwrite=True)
            self.assertEqual(result['case_count'], len(GOLDEN_CASES))
            manifest = json.loads(Path(result['manifest']).read_text(encoding='utf-8'))
            self.assertTrue(manifest['local_only'])
            self.assertFalse(manifest['mouse_input'])
            self.assertFalse(manifest['screen_capture'])
            self.assertFalse(manifest['network'])
            self.assertFalse(manifest['user_image_data'])
            for case in manifest['cases']:
                self.assertTrue((Path(tmp) / case['file']).is_file())

    def test_good_planner_passes_all_golden_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(fake_plan_good, {'profile_key': 'microsoft-paint'}, directory=tmp)
            self.assertTrue(result['passed'])
            self.assertEqual(result['failed_count'], 0)
            text = format_result(result)
            self.assertIn('Golden image regression: 4/4 passed', text)
            self.assertIn('yellow-banana-hue-guard PASS', text)

    def test_yellow_to_pink_regression_fails_hue_and_color_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(fake_plan_yellow_to_pink, {}, cases=[GOLDEN_CASES[0]], directory=tmp)
            self.assertFalse(result['passed'])
            row = result['rows'][0]
            self.assertFalse(row['passed'])
            self.assertTrue(any('hue' in reason for reason in row['failures']))
            self.assertTrue(any('perceptual' in reason for reason in row['failures']))

    def test_suite_reports_no_mouse_screen_network_or_user_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(fake_plan_good, {}, directory=tmp)
            self.assertTrue(result['local_only'])
            self.assertFalse(result['mouse_input'])
            self.assertFalse(result['screen_capture'])
            self.assertFalse(result['network'])
            self.assertFalse(result['user_image_data'])

    def test_release_build_collects_step17_module_docs_and_assets(self):
        source = Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'GoldenImageRegression'", source)
        self.assertIn('STEP-17-GOLDEN-IMAGE-REGRESSION.md', source)
        self.assertIn('golden-regression', source)
        self.assertTrue(Path('STEP-17-GOLDEN-IMAGE-REGRESSION.md').is_file())
        self.assertTrue(Path('golden-regression/manifest.json').is_file())


if __name__ == '__main__':
    unittest.main()
