import unittest
from PIL import Image, ImageDraw

from ResourceAllocation import (CPU_WORKER_CHOICES, RAM_BUDGETS, resolve_allocation,
                                resolve_cpu_workers, resolve_ram_budget_mb)
from PixelData import build_strokes
from AdvancedColor import build_color_strokes
from DrawBot import make_plan


class ResourceAllocationTests(unittest.TestCase):
    def test_allocation_resolves_safe_defaults(self):
        meta = resolve_allocation('Auto', 'Auto', 'Auto', '4096')
        self.assertGreaterEqual(meta['cpu_workers_resolved'], 1)
        self.assertGreaterEqual(meta['logical_cpus'], meta['cpu_workers_resolved'])
        self.assertGreaterEqual(meta['ram_budget_mb'], 128)
        self.assertIn(meta['cpu_workers'], CPU_WORKER_CHOICES)

    def test_custom_ram_validation(self):
        self.assertEqual(resolve_ram_budget_mb('Custom', '512'), 512)
        with self.assertRaises(ValueError):
            resolve_ram_budget_mb('Custom', '12')

    def test_parallel_basic_strokes_match_serial(self):
        image = Image.new('RGBA', (260, 240), 'white')
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 7, 210, 60), fill=(0, 0, 0, 255))
        draw.rectangle((30, 110, 240, 190), fill=(255, 0, 19, 255))
        serial = build_strokes(image, True, True)
        parallel = build_strokes(image, True, True, cpu_workers=2, cpu_engine='Threads', ram_budget_mb=512)
        self.assertEqual(serial, parallel)

    def test_parallel_advanced_color_matches_serial(self):
        image = Image.new('RGBA', (260, 220), 'white')
        draw = ImageDraw.Draw(image)
        for y in range(0, 220, 5):
            color = (y % 255, 80, 220 - (y % 180), 255)
            draw.rectangle((0, y, 259, min(219, y + 3)), fill=color)
        serial, _ = build_color_strokes(image, color_rendering='Perceptual match', color_layers='Off')
        parallel, meta = build_color_strokes(image, color_rendering='Perceptual match', color_layers='Off',
                                             cpu_workers=2, cpu_engine='Threads', ram_budget_mb=512)
        self.assertEqual(serial, parallel)
        self.assertIn(meta['cpu_backend'], ('threads', 'serial'))

    def test_plan_carries_resource_metadata(self):
        image = Image.new('RGBA', (80, 60), 'black')
        plan = make_plan(image, (320, 240), dict(detail=8, delay=.01, lines=True,
                                                 skip_white=True, contrast=1, outline=False,
                                                 drawing_mode='Lines (fastest)', speed='Balanced',
                                                 precision='High', brush_px=2, max_seconds=180,
                                                 cpu_workers='2', cpu_engine='Threads',
                                                 ram_budget='512 MB', ram_custom_mb='4096'))
        self.assertEqual(plan['options']['cpu_workers_resolved'], min(2, resolve_cpu_workers('All logical')))
        self.assertEqual(plan['options']['ram_budget_mb'], 512)


if __name__ == '__main__':
    unittest.main()
