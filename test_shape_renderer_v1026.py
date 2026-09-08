import unittest
from PIL import Image, ImageDraw

from DrawBot import make_plan
from ShapePaths import build_shape_execution_paths, validate_shape_model
from ContinuousPaths import SHAPE_PATH_MODE


def base_options(**overrides):
    data = dict(
        detail=8, delay=.003, speed='Fast', precision='Normal', lines=True,
        drawing_mode=SHAPE_PATH_MODE, shape_order='Fill first', shape_model='Better shapes v2',
        max_stroke_cap='Unlimited', progressive_rendering='On', planning_watchdog='On',
        paint_current_color=True, erase_mode=False, render_style='Standard / pixel',
        draw_quality='Balanced', human_mode='Off', gpu_mode='CPU', gpu_vram='Auto',
        gpu_performance='Balanced', cpu_workers_resolved=1, cpu_workers='1', cpu_engine='Auto',
        ram_budget='512 MB', ram_budget_mb=512, logical_cpus=1, background_fill='Off',
        background_simplification='Off', color_grouping='Accurate', color_rendering='RGB nearest',
        color_layers='Off', custom_color_workflow='Calibrated palette', preview_mode='Manual',
        tool_strategy='Auto', portrait_focus=False, skip_white=True, contrast=1.0,
        outline=False, brush_px=3, max_seconds=90, time_budget_mode='Manual',
        time_budget_seconds=90, time_budget_active=False, target_stroke_count='Unlimited',
        target_stroke_count_resolved=None,
    )
    data.update(overrides)
    return data


class BetterShapesV2Tests(unittest.TestCase):
    def test_validate_shape_model(self):
        self.assertEqual(validate_shape_model('Better shapes v2'), 'Better shapes v2')
        with self.assertRaises(ValueError):
            validate_shape_model('wrong')

    def test_dense_shape_uses_fewer_paths_and_silhouette(self):
        groups = [[(0, y, 29, y) for y in range(18)]]
        fast, fast_meta = build_shape_execution_paths(groups, brush_px=3, shape_model='Fast raster', stroke_cap='Unlimited')
        better, better_meta = build_shape_execution_paths(groups, brush_px=3, shape_model='Better shapes v2', stroke_cap='Unlimited')
        self.assertFalse(fast_meta['shape_v2_enabled'])
        self.assertTrue(better_meta['shape_v2_enabled'])
        self.assertLess(sum(map(len, better)), sum(map(len, fast)))
        self.assertTrue(any(len(path) >= 4 and path[0] == path[-1] for path in better[0]))

    def test_make_plan_records_better_shapes_meta(self):
        im = Image.new('RGBA', (64, 40), 'white')
        draw = ImageDraw.Draw(im)
        draw.rounded_rectangle((7, 7, 55, 32), radius=8, fill='black')
        plan = make_plan(im, (640, 400), base_options())
        self.assertEqual(plan['path_stats']['shape_model'], 'Better shapes v2')
        self.assertTrue(plan['path_stats']['shape_v2_enabled'])
        self.assertGreaterEqual(plan['path_stats']['shape_components'], 1)
        self.assertLess(plan['count'], plan['source_count'])

    def test_fast_raster_model_is_still_available(self):
        groups = [[(2, y, 22, y) for y in range(12)]]
        _paths, meta = build_shape_execution_paths(groups, brush_px=2, shape_model='Fast raster', stroke_cap='Unlimited')
        self.assertEqual(meta['shape_model'], 'Fast raster')
        self.assertFalse(meta['shape_v2_enabled'])


if __name__ == '__main__':
    unittest.main()
