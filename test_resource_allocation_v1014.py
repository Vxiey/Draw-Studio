import unittest
from PIL import Image, ImageDraw

from ResourceAllocation import (PLANNING_RESOLUTION_MODES, benchmark_allocation,
                                resolve_planning_limits)
from PixelData import prepare_image
from DrawBot import make_plan


class ResourceAllocationV1014Tests(unittest.TestCase):
    def test_standard_resolution_keeps_legacy_sample_size(self):
        limits = resolve_planning_limits(9, (720, 480), planning_resolution='Standard',
                                         cpu_workers=16, ram_budget_mb=8192)
        self.assertEqual(limits['planning_resolution_effective'], 'Standard')
        self.assertEqual(limits['planner_sample_limit'], 100)
        image, _ = prepare_image(Image.new('RGBA', (180, 120)), (720, 480), 9,
                                 sample_limit=limits['planner_sample_limit'],
                                 max_pixels=limits['planner_max_pixels'])
        self.assertEqual(image.size, (100, 67))

    def test_ultra_resolution_increases_planning_pixels(self):
        standard = resolve_planning_limits(10, (1200, 700), planning_resolution='Standard',
                                           cpu_workers=16, ram_budget_mb=8192)
        ultra = resolve_planning_limits(10, (1200, 700), planning_resolution='Ultra',
                                        cpu_workers=16, ram_budget_mb=8192)
        self.assertGreater(ultra['planner_sample_limit'], standard['planner_sample_limit'])
        self.assertGreater(ultra['planner_max_pixels'], standard['planner_max_pixels'])

    def test_make_plan_carries_planning_resolution_metadata(self):
        image = Image.new('RGBA', (240, 160), 'white')
        ImageDraw.Draw(image).rectangle((20, 20, 180, 110), fill=(255, 120, 41, 255))
        plan = make_plan(image, (960, 640), dict(detail=9, delay=.01, lines=True,
                                                 skip_white=True, contrast=1, outline=False,
                                                 drawing_mode='Smart paths (recommended)',
                                                 speed='Balanced', precision='High', brush_px=2,
                                                 max_seconds=600, planning_resolution='High',
                                                 cpu_workers='4', cpu_engine='Threads',
                                                 ram_budget='2 GB', ram_custom_mb='4096',
                                                 color_rendering='Perceptual match',
                                                 color_layers='Off', custom_color_workflow='Calibrated palette',
                                                 background_fill='Off', background_simplification='Off',
                                                 color_grouping='Accurate'))
        self.assertEqual(plan['options']['planning_resolution_effective'], 'High')
        self.assertGreater(plan['image'].width, 100)
        self.assertIn(plan['options']['planning_resolution'], PLANNING_RESOLUTION_MODES)

    def test_cpu_benchmark_returns_backend_and_score(self):
        result = benchmark_allocation('2', 'Threads', '512 MB', '4096', loops_per_worker=2000)
        self.assertEqual(result['benchmark_tasks'], min(2, result['logical_cpus']))
        self.assertIn(result['benchmark_backend'], ('threads', 'serial'))
        self.assertGreaterEqual(result['benchmark_score'], 0)


if __name__ == '__main__':
    unittest.main()
