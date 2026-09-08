import unittest
from PIL import Image, ImageDraw

from PortraitPlanner import (prepare_portrait_image, portrait_sample_limit,
                             portrait_strokes)


class PortraitPlannerTests(unittest.TestCase):
    def test_portrait_samples_more_detail_than_legacy(self):
        self.assertGreater(portrait_sample_limit(8), 100)
        self.assertGreater(portrait_sample_limit(10), portrait_sample_limit(8))

    def test_prepare_keeps_aspect_ratio(self):
        image = Image.new('RGB', (400, 200), 'gray')
        gray, fitted = prepare_portrait_image(image, (800, 600), 8)
        self.assertEqual(round(fitted[0] / fitted[1], 3), 2.0)
        self.assertEqual(round(gray.width / gray.height, 3), 2.0)

    def test_dark_regions_receive_more_tone_than_light(self):
        image = Image.new('L', (120, 80), 245)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 59, 79), fill=45)
        groups, stats = portrait_strokes(image, detail=8, lines=True, include_edges=False)
        left = right = 0
        for x1, y1, x2, y2 in groups[0]:
            midpoint = (x1 + x2) / 2
            if midpoint < 60: left += 1
            else: right += 1
        self.assertGreater(left, right * 3 + 5)
        self.assertGreater(stats.tone_strokes, 0)

    def test_portrait_contains_multiple_stroke_directions(self):
        image = Image.new('L', (100, 100), 80)
        groups, _ = portrait_strokes(image, detail=9, lines=True, include_edges=False)
        vectors = {(0 if x2 == x1 else 1 if y2 == y1 else 2)
                   for x1, y1, x2, y2 in groups[0]}
        self.assertIn(0, vectors)  # vertical
        self.assertIn(1, vectors)  # horizontal
        self.assertIn(2, vectors)  # diagonal

    def test_edges_add_contour_strokes(self):
        image = Image.new('L', (100, 80), 245)
        ImageDraw.Draw(image).ellipse((25, 10, 75, 70), fill=60)
        no_edges, _ = portrait_strokes(image, 8, True, include_edges=False)
        with_edges, stats = portrait_strokes(image, 8, True, include_edges=True)
        self.assertGreater(stats.edge_strokes, 0)
        self.assertGreater(len(with_edges[0]), len(no_edges[0]))

    def test_dots_are_points(self):
        image = Image.new('L', (24, 24), 80)
        groups, _ = portrait_strokes(image, 8, False)
        self.assertTrue(groups[0])
        self.assertTrue(all((x1, y1) == (x2, y2) for x1, y1, x2, y2 in groups[0]))

    def test_subject_focus_lightens_outer_background_more_than_center(self):
        image = Image.new('RGB', (200, 200), (90, 90, 90))
        focused, _ = prepare_portrait_image(image, (400, 400), 8, subject_focus=True)
        plain, _ = prepare_portrait_image(image, (400, 400), 8, subject_focus=False)
        self.assertGreater(focused.getpixel((2, 2)), plain.getpixel((2, 2)))
        c = focused.width // 2
        self.assertLessEqual(abs(focused.getpixel((c, c)) - plain.getpixel((c, c))), 2)

    def test_cancellation_is_honoured(self):
        image = Image.new('L', (120, 120), 80)
        with self.assertRaises(InterruptedError):
            portrait_strokes(image, 10, True, cancelled=lambda: True)


if __name__ == '__main__':
    unittest.main()
