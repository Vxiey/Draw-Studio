import unittest

from PIL import Image, ImageDraw

from AccuracyEvaluator import evaluate_preview, VISUAL_ACCURACY_WEIGHTS


class SourceRelativeAccuracyV10125Tests(unittest.TestCase):
    def test_a_identical_source_is_near_100(self):
        src = Image.new('RGB', (48, 32), (235, 196, 35))
        meta = evaluate_preview(src, src.copy(), coverage_percent=100.0,
                                plan_execution_accuracy_percent=100.0)
        for key in ('source_pixel_accuracy_percent', 'perceptual_color_accuracy_percent',
                    'luminance_accuracy_percent', 'hue_accuracy_percent',
                    'edge_accuracy_percent', 'visual_accuracy_percent'):
            self.assertGreaterEqual(meta[key], 99.9, key)
        self.assertEqual(meta['coverage_percent'], 100.0)
        self.assertEqual(meta['plan_execution_accuracy_percent'], 100.0)

    def test_b_yellow_replaced_with_pink_reduces_source_color_and_hue_accuracy(self):
        src = Image.new('RGB', (64, 64), (242, 200, 35))
        pink = Image.new('RGB', (64, 64), (244, 142, 160))
        meta = evaluate_preview(src, pink, coverage_percent=100.0,
                                plan_execution_accuracy_percent=100.0)
        self.assertLess(meta['perceptual_color_accuracy_percent'], 80.0)
        self.assertLess(meta['hue_accuracy_percent'], 80.0)
        self.assertLess(meta['visual_accuracy_percent'], 90.0)
        self.assertEqual(meta['plan_execution_accuracy_percent'], 100.0)
        self.assertIn('plan differs from the source', meta.get('plan_source_divergence_note', ''))

    def test_c_same_hue_much_darker_reduces_luminance_accuracy(self):
        src = Image.new('RGB', (32, 32), (240, 190, 30))
        dark = Image.new('RGB', (32, 32), (95, 72, 8))
        exact = evaluate_preview(src, src.copy(), coverage_percent=100.0)
        meta = evaluate_preview(src, dark, coverage_percent=100.0)
        self.assertLess(meta['luminance_accuracy_percent'], exact['luminance_accuracy_percent'] - 15.0)

    def test_d_missing_area_reduces_coverage_and_visual_accuracy(self):
        src = Image.new('RGB', (64, 64), 'white')
        d = ImageDraw.Draw(src)
        d.rectangle((8, 8, 55, 55), fill=(220, 40, 35))
        partial = src.copy()
        ImageDraw.Draw(partial).rectangle((32, 8, 55, 55), fill='white')
        full = evaluate_preview(src, src.copy(), coverage_percent=100.0)
        missing = evaluate_preview(src, partial, coverage_percent=50.0)
        self.assertEqual(missing['coverage_percent'], 50.0)
        self.assertLess(missing['visual_accuracy_percent'], full['visual_accuracy_percent'])

    def test_e_internal_target_can_be_perfect_while_source_similarity_is_not(self):
        src = Image.new('RGB', (40, 40), (245, 205, 25))
        planned_and_rendered = Image.new('RGB', (40, 40), (240, 130, 150))
        meta = evaluate_preview(src, planned_and_rendered, coverage_percent=100.0,
                                plan_execution_accuracy_percent=100.0,
                                return_error_map=True)
        self.assertEqual(meta['plan_execution_accuracy_percent'], 100.0)
        self.assertLess(meta['source_pixel_accuracy_percent'], 100.0)
        self.assertLess(meta['visual_accuracy_percent'], 100.0)
        self.assertEqual(meta['_error_map_image'].size, src.size)

    def test_coverage_is_not_faked_when_not_supplied(self):
        src = Image.new('RGB', (16, 16), 'white')
        meta = evaluate_preview(src, src.copy())
        self.assertNotIn('coverage_percent', meta)
        self.assertEqual(VISUAL_ACCURACY_WEIGHTS['coverage_percent'], 0.15)


if __name__ == '__main__':
    unittest.main()
