import json
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from PostDrawCorrectionPass import build_post_draw_correction_plan, compact_correction_meta, correction_needed
from PreviewDiagnostics import build_preview_diagnostics, format_preview_diagnostics


def source_image():
    im = Image.new('RGB', (80, 50), 'white')
    d = ImageDraw.Draw(im)
    d.rectangle((10, 10, 70, 40), fill=(242, 205, 31))
    d.rectangle((45, 18, 62, 32), fill=(50, 150, 82))
    return im


def trusted_meta(**updates):
    meta = {
        'available': True, 'trusted': True, 'feedback_trust': 'high',
        'visual_accuracy_percent': 71.0, 'perceptual_color_accuracy_percent': 72.0,
        'actual_coverage_percent': 84.0, 'unexpected_ink_percent': 0.0,
        'actual_vs_simulated_visual_percent': 88.0, 'visual_gate_percent': 76.0,
        'blank_canvas': False,
    }
    meta.update(updates)
    return meta


class Step14PostDrawCorrectionTests(unittest.TestCase):
    def test_trusted_missing_area_builds_bounded_paths_without_pixels(self):
        src = source_image()
        actual = src.copy()
        ImageDraw.Draw(actual).rectangle((20, 16, 45, 28), fill='white')
        corr = build_post_draw_correction_plan(
            original_source=src, actual_canvas=actual, palette_rgb=((242,205,31),(50,150,82),(80,50,10)),
            post_draw_meta=trusted_meta(), comparison_size=src.size,
            quantized_target=src.copy(), simulated_final=src.copy(),
            options={'profile_key':'microsoft-paint','profile_name':'Microsoft Paint','speed':'Fast'},
            usable_deadline_seconds=80.0, elapsed_seconds=50.0, visual_gate_percent=76.0,
            max_paths=40, max_pixels=2000)
        self.assertTrue(corr['enabled'])
        self.assertTrue(corr['safe'])
        self.assertGreater(corr['selected_correction_pixels'], 0)
        self.assertGreater(corr['correction_paths'], 0)
        self.assertLessEqual(corr['correction_paths'], 40)
        self.assertFalse(corr['stores_image_data'])
        payload = json.dumps(compact_correction_meta(corr)).lower()
        self.assertNotIn('screenshot', payload)
        self.assertNotIn('thumbnail', payload)
        self.assertNotIn('source_pixels', payload)
        self.assertNotIn('canvas_pixels', payload)
        self.assertNotIn('crop_box', payload)

    def test_colour_error_uses_nearest_oklab_plan_colour(self):
        src = Image.new('RGB', (32, 20), 'white')
        ImageDraw.Draw(src).rectangle((4, 4, 27, 15), fill=(242, 205, 31))
        actual = Image.new('RGB', src.size, 'white')
        ImageDraw.Draw(actual).rectangle((4, 4, 27, 15), fill=(240, 120, 170))
        corr = build_post_draw_correction_plan(
            original_source=src, actual_canvas=actual,
            palette_rgb=((242,205,31),(240,120,170),(255,255,255)),
            post_draw_meta=trusted_meta(actual_coverage_percent=100.0, visual_accuracy_percent=68.0),
            comparison_size=src.size, quantized_target=src.copy(), options={'speed':'Fast'},
            usable_deadline_seconds=80.0, elapsed_seconds=40.0, visual_gate_percent=76.0)
        self.assertTrue(corr['enabled'])
        self.assertIn(0, corr['color_order'])
        self.assertNotIn(1, corr['color_order'][:1])

    def test_low_trust_or_unexpected_ink_skips(self):
        src = source_image()
        low = build_post_draw_correction_plan(
            original_source=src, actual_canvas=src.copy(), palette_rgb=((242,205,31),),
            post_draw_meta=trusted_meta(feedback_trust='low', trusted=False), comparison_size=src.size)
        self.assertFalse(low['enabled'])
        self.assertIn('not trusted', low['reason'])
        unsafe = build_post_draw_correction_plan(
            original_source=src, actual_canvas=src.copy(), palette_rgb=((242,205,31),),
            post_draw_meta=trusted_meta(unexpected_ink_percent=40.0), comparison_size=src.size)
        self.assertFalse(unsafe['enabled'])
        self.assertIn('unexpected ink', unsafe['reason'])

    def test_deadline_headroom_blocks_large_correction(self):
        src = source_image()
        actual = Image.new('RGB', src.size, 'white')
        corr = build_post_draw_correction_plan(
            original_source=src, actual_canvas=actual, palette_rgb=((242,205,31),(50,150,82)),
            post_draw_meta=trusted_meta(actual_coverage_percent=20.0), comparison_size=src.size,
            options={'speed':'Fast'}, usable_deadline_seconds=80.0, elapsed_seconds=79.2)
        self.assertFalse(corr['enabled'])
        self.assertIn('headroom', corr['reason'])

    def test_correction_needed_recognizes_quality_gate(self):
        needed, reason = correction_needed(trusted_meta(actual_coverage_percent=99.0, visual_accuracy_percent=70.0), visual_gate_percent=76.0)
        self.assertTrue(needed)
        self.assertIn('Visual Accuracy', reason)
        ok, reason2 = correction_needed(trusted_meta(actual_coverage_percent=99.0, visual_accuracy_percent=88.0, perceptual_color_accuracy_percent=93.0), visual_gate_percent=76.0)
        self.assertFalse(ok)
        self.assertIn('within', reason2)

    def test_preview_diagnostics_reports_correction_pass(self):
        meta = build_preview_diagnostics({'post_draw_correction_meta': {
            'enabled': True, 'safe': True, 'correction_paths': 12, 'executed_paths': 10,
            'selected_correction_pixels': 240, 'corrected_colors': 2,
            'post_correction_visual_accuracy_percent': 83.4, 'stores_image_data': False,
        }})
        text = format_preview_diagnostics(meta)
        self.assertIn('Correction pass:', text)
        self.assertIn('10/12 paths', text)
        self.assertIn('post Visual 83.4%', text)

    def test_release_build_collects_step14_module_and_doc(self):
        source = Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'PostDrawCorrectionPass'", source)
        self.assertIn('STEP-14-POST-DRAW-CORRECTION-PASS.md', source)
        self.assertTrue(Path('STEP-14-POST-DRAW-CORRECTION-PASS.md').is_file())


if __name__ == '__main__':
    unittest.main()
