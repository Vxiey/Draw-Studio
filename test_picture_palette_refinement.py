import unittest

import numpy as np
from PIL import Image

from PicturePaletteRefinement import refine_picture_palette
from PixelAccuratePlanner import _to_oklab, exact_palette_map


def error(image, colors):
    indices, _, rgb, _ = exact_palette_map(image, colors, gpu_mode='CPU', skip_white=False, color_fidelity='Exact')
    distance = np.linalg.norm(_to_oklab(rgb) - _to_oklab(np.asarray(colors, dtype=np.uint8)[indices]), axis=-1)
    return float(np.mean(distance ** 2)), float(np.percentile(distance, 95))


class PicturePaletteRefinementTests(unittest.TestCase):
    def test_unused_slots_preserve_more_gray_and_skin_shades(self):
        t = np.linspace(0, 1, 128)[:, None]
        gray = np.tile(np.rint(t * 255), (1, 3))
        skin = np.rint((70, 43, 30) + t * np.array((160, 162, 151)))
        pixels = np.vstack((np.tile(gray[None], (24, 1, 1)), np.tile(skin[None], (24, 1, 1)))).astype(np.uint8)
        source = Image.fromarray(pixels)
        seeds = ((0,0,0), (85,85,85), (170,170,170), (255,255,255), (70,43,30), (230,205,181))
        refined = refine_picture_palette(source, seeds, 16)
        self.assertLessEqual(len(refined), 16)
        self.assertGreater(len(refined), len(seeds))
        before, after = error(source, seeds), error(source, refined)
        self.assertLess(after[0], before[0] * .45)
        self.assertLess(after[1], before[1])
        self.assertEqual(refined, refine_picture_palette(source, seeds, 16))

    def test_refinement_preserves_small_saturated_accent(self):
        levels = np.arange(64, dtype=np.uint8) * 4
        pixels = np.tile(levels[None, :, None], (64, 1, 3))
        pixels[0,0] = (0,255,0)
        source = Image.fromarray(pixels)
        seeds = ((0,0,0), (84,84,84), (168,168,168), (252,252,252), (0,255,0))
        refined = refine_picture_palette(source, seeds, 12)
        self.assertIn((0,255,0), refined)
        self.assertLessEqual(error(source, refined)[0], error(source, seeds)[0])

    def test_flat_image_needs_only_its_exact_source_color(self):
        source = Image.new('RGB', (32,32), (142,96,71))
        self.assertEqual(refine_picture_palette(source, ((142,96,71),), 24), ((142,96,71),))

    def test_cancellation_interrupts_refinement(self):
        with self.assertRaises(InterruptedError):
            refine_picture_palette(Image.new('RGB',(32,32)), ((0,0,0),), 24, cancelled=lambda: True)


if __name__ == '__main__':
    unittest.main()
