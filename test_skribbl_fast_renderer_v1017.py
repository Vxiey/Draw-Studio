import unittest
from PIL import Image

from ContinuousPaths import DRAWING_MODES, SHAPE_PATH_MODE
from GameProfiles import PROFILES
from PaletteMaps import PRESETS
from ShapePaths import build_shape_execution_paths, validate_shape_order, validate_stroke_cap
from DrawBot import make_plan


def base_options(**overrides):
    opts = dict(detail=8, delay=.003, speed='Fast', precision='Normal', lines=True,
                drawing_mode=SHAPE_PATH_MODE, shape_order='Fill first', max_stroke_cap='2500',
                skip_white=True, contrast=1, outline=False, brush_px=3, max_seconds=180,
                paint_current_color=True, erase_mode=False, render_style='Standard / pixel',
                draw_quality='Balanced', human_mode='Off', gpu_mode='CPU', gpu_vram='Auto',
                gpu_performance='Balanced', cpu_workers='Auto', cpu_engine='Threads',
                ram_budget='Auto', ram_custom_mb='4096', planning_resolution='Standard',
                background_fill='Off', background_simplification='Strong', color_grouping='Reduced palette',
                color_rendering='RGB nearest', color_layers='Off', custom_color_workflow='Calibrated palette',
                preview_mode='Manual', tool_strategy='Auto', portrait_focus=True,
                paint_tool='Use current tool', effective_paint_tool='Use current tool', tool_actions=[],
                fill_tool_available=False, fill_tool_actions=[], fill_restore_actions=[])
    opts.update(overrides)
    return opts


class SkribblFastRendererTests(unittest.TestCase):
    def test_profile_and_mode_are_registered(self):
        self.assertIn('Skribbl.io Fast', PROFILES)
        self.assertEqual(PROFILES['Skribbl.io Fast'][0], 'skribbl-fast')
        self.assertIn('skribbl-fast', PRESETS)
        self.assertIn(SHAPE_PATH_MODE, DRAWING_MODES)

    def test_shape_settings_validate(self):
        self.assertEqual(validate_shape_order('Fill first'), 'Fill first')
        self.assertEqual(validate_shape_order('Contour first'), 'Contour first')
        self.assertEqual(validate_stroke_cap('2500'), '2500')
        with self.assertRaises(ValueError):
            validate_shape_order('Random')
        with self.assertRaises(ValueError):
            validate_stroke_cap('123')

    def test_shape_paths_reduce_filled_blocks_and_report_skips(self):
        # 20 exact source runs plus one isolated one-pixel detail.
        group = [(0, y, 19, y) for y in range(20)] + [(40, 40, 40, 40)]
        paths, meta = build_shape_execution_paths([group], brush_px=3, stroke_cap='Unlimited')
        self.assertLess(meta['execution_paths'], meta['source_strokes'])
        self.assertGreater(meta['skipped_tiny_details'], 0)
        self.assertEqual(meta['shape_order'], 'Fill first')
        self.assertTrue(paths[0])

    def test_shape_cap_is_applied(self):
        group = [(i * 3, 0, i * 3 + 1, 0) for i in range(30)]
        _paths, meta = build_shape_execution_paths([group], brush_px=1, stroke_cap='1000')
        self.assertLessEqual(meta['execution_paths'], 1000)
        _paths, meta = build_shape_execution_paths([group], brush_px=1, stroke_cap='1000')
        self.assertEqual(meta['max_stroke_cap_resolved'], 1000)

    def test_make_plan_uses_shape_path_metadata(self):
        im = Image.new('RGBA', (40, 30), 'white')
        for y in range(5, 25):
            for x in range(6, 34):
                im.putpixel((x, y), (0, 0, 0, 255))
        plan = make_plan(im, (400, 300), base_options(max_stroke_cap='1000'))
        self.assertEqual(plan['path_stats']['mode'], 'Shape paths')
        self.assertLessEqual(plan['count'], 1000)
        self.assertGreater(plan['source_count'], plan['count'])


if __name__ == '__main__':
    unittest.main()
