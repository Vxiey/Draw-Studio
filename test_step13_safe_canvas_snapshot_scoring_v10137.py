import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from SafeCanvasSnapshotScoring import score_final_canvas_snapshot, crop_fitted_canvas
from AutoTunerFeedback import record_completed_feedback


def source_image():
    im = Image.new('RGB', (80, 50), 'white')
    d = ImageDraw.Draw(im)
    d.rectangle((10, 10, 70, 40), fill=(242, 205, 31))
    d.line((10, 10, 70, 40), fill=(80, 50, 10), width=2)
    return im


def plan_for(post_draw, *, usable=80.0):
    return {
        'options': {
            'profile_key': 'microsoft-paint', 'profile_name': 'Microsoft Paint',
            'paint_tool': 'Brush', 'brush_px': 1, 'custom_color_workflow': 'Adaptive exact (recommended)',
            'time_budget_seconds': usable, 'time_budget_active': True,
            'auto_tuner_meta': {
                'active': True, 'selected_strategy': 'deadline-hybrid-fast',
                'source_features': {'source_kind': 'flat illustration'},
                'acceptance_gates': {'visual_accuracy_min_percent': 76.0, 'usable_deadline_seconds': usable},
            },
            'auto_tuner_acceptance_meta': {
                'usable_deadline_seconds': usable,
                'gates': {'visual_accuracy_min_percent': 76.0, 'usable_deadline_seconds': usable},
            },
            'adaptive_accuracy_meta': {
                'visual_accuracy_percent': 90.0, 'coverage_percent': 100.0,
                'perceptual_color_accuracy_percent': 90.0, 'edge_accuracy_percent': 90.0,
                'plan_execution_accuracy_percent': 100.0,
            },
            'post_draw_accuracy_meta': post_draw,
        },
        'estimate': 50.0, 'draw_time_estimate': {'projected_seconds': 50.0},
        'count': 100, 'plan_area': (80, 50),
    }


class Step13SafeCanvasSnapshotScoringTests(unittest.TestCase):
    def test_crop_fitted_canvas_handles_centered_fit_without_saving_pixels(self):
        snap = Image.new('RGB', (120, 80), 'white')
        d = ImageDraw.Draw(snap)
        d.rectangle((20, 15, 99, 64), fill=(242, 205, 31))
        crop, meta = crop_fitted_canvas(snap, area=(0, 0, 120, 80), fitted=(80, 50))
        self.assertEqual(crop.size, (80, 50))
        self.assertTrue(meta['geometry_ok'])
        self.assertEqual(meta['crop_box'], (20, 15, 100, 65))

    def test_identical_final_canvas_scores_high_trust(self):
        src = source_image()
        meta = score_final_canvas_snapshot(
            snapshot=src.copy(), original_source=src, area=(0, 0, 80, 50), fitted=(80, 50),
            comparison_size=(80, 50), simulated_final=src.copy(), profile_key='microsoft-paint',
            actual_elapsed_seconds=20.0, usable_deadline_seconds=80.0, visual_gate_percent=76.0)
        self.assertTrue(meta['available'])
        self.assertTrue(meta['trusted'])
        self.assertEqual(meta['feedback_trust'], 'high')
        self.assertGreaterEqual(meta['visual_accuracy_percent'], 99.0)
        self.assertGreaterEqual(meta['actual_vs_simulated_visual_percent'], 99.0)
        self.assertFalse(meta['capture_pixels_persisted'])
        self.assertFalse(meta['stores_image_data'])

    def test_blank_canvas_is_scored_but_not_trusted(self):
        src = source_image()
        blank = Image.new('RGB', src.size, 'white')
        meta = score_final_canvas_snapshot(
            snapshot=blank, original_source=src, area=(0, 0, 80, 50), fitted=(80, 50),
            comparison_size=(80, 50), simulated_final=src.copy(), profile_key='gartic-phone',
            actual_elapsed_seconds=80.0, usable_deadline_seconds=80.0, visual_gate_percent=76.0)
        self.assertTrue(meta['available'])
        self.assertFalse(meta['trusted'])
        self.assertIn(meta['feedback_trust'], ('low', 'none'))
        self.assertTrue(meta['blank_canvas'])
        self.assertIn('blank-or-nearly-blank-canvas', meta['reasons'])
        self.assertLess(meta['actual_coverage_percent'], 5.0)

    def test_actual_vs_simulated_detects_physical_result_mismatch(self):
        src = source_image()
        simulated = src.copy()
        actual = Image.new('RGB', src.size, 'white')
        ImageDraw.Draw(actual).rectangle((10, 10, 70, 40), fill=(240, 120, 160))
        meta = score_final_canvas_snapshot(
            snapshot=actual, original_source=src, area=(0, 0, 80, 50), fitted=(80, 50),
            comparison_size=(80, 50), simulated_final=simulated, profile_key='microsoft-paint',
            actual_elapsed_seconds=22.0, usable_deadline_seconds=80.0, visual_gate_percent=76.0)
        self.assertTrue(meta['available'])
        self.assertLess(meta['visual_accuracy_percent'], 90.0)
        self.assertLess(meta['actual_vs_simulated_visual_percent'], 90.0)
        self.assertIsNotNone(meta['delta_e_oklab']['mean_delta_e_oklab'])

    def test_feedback_uses_only_trusted_real_snapshot_metrics(self):
        src = source_image()
        meta = score_final_canvas_snapshot(
            snapshot=src.copy(), original_source=src, area=(0, 0, 80, 50), fitted=(80, 50),
            comparison_size=(80, 50), simulated_final=src.copy(), profile_key='microsoft-paint',
            actual_elapsed_seconds=20.0, usable_deadline_seconds=80.0, visual_gate_percent=76.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'feedback.json'
            result = record_completed_feedback(plan_for(meta), 20.0, completed_paths=100, path=path)
            self.assertTrue(result['recorded'])
            self.assertEqual(result['result_source'], 'post-draw canvas snapshot')
            self.assertEqual(result['snapshot_scoring_state'], 'verified')
            self.assertGreaterEqual(result['snapshot_confidence_percent'], 80.0)
            raw = json.loads(path.read_text(encoding='utf-8'))
            payload = json.dumps(raw).lower()
            self.assertNotIn('image_data', payload)
            self.assertNotIn('thumbnail', payload)
            self.assertNotIn('screenshot', payload)
            self.assertNotIn('crop_box', payload)

    def test_preview_diagnostics_exposes_real_result_summary(self):
        from PreviewDiagnostics import build_preview_diagnostics, format_preview_diagnostics
        meta = build_preview_diagnostics({
            'profile_key': 'microsoft-paint',
            'post_draw_accuracy_meta': {
                'available': True, 'trusted': True, 'feedback_trust': 'high', 'scoring_state': 'verified',
                'confidence_percent': 94.0, 'visual_accuracy_percent': 88.0,
                'actual_coverage_percent': 97.0, 'actual_vs_simulated_visual_percent': 91.0,
            }
        })
        text = format_preview_diagnostics(meta)
        self.assertIn('Real result:', text)
        self.assertIn('trust high', text)
        self.assertIn('actual Visual 88.0%', text)

    def test_release_build_collects_step13_module_and_doc(self):
        source = Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'SafeCanvasSnapshotScoring'", source)
        self.assertIn('STEP-13-REAL-RESULT-VERIFICATION.md', source)
        self.assertTrue(Path('STEP-13-REAL-RESULT-VERIFICATION.md').is_file())


if __name__ == '__main__':
    unittest.main()
