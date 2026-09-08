import unittest
from PIL import Image, ImageDraw
from EdgeDetection import verify_canvas_edges, verify_canvas_edges_from_capture


class CanvasEdgeDetectionTests(unittest.TestCase):
    def test_exact_visible_edges_pass(self):
        image = Image.new('RGB', (120, 100), (178, 178, 178))
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 89, 69), fill=(255, 255, 255))
        result = verify_canvas_edges(image, (10, 10, 80, 60), tolerance_px=4)
        self.assertTrue(result.ok, result.as_dict())
        self.assertGreaterEqual(result.detected_sides, 4)
        self.assertLessEqual(result.max_offset_px, 4)

    def test_clear_shifted_edge_stops(self):
        image = Image.new('RGB', (120, 100), (178, 178, 178))
        draw = ImageDraw.Draw(image)
        # The actual canvas starts 7 px to the right of the saved selection.
        draw.rectangle((17, 10, 96, 69), fill=(255, 255, 255))
        result = verify_canvas_edges(image, (10, 10, 80, 60), tolerance_px=4)
        self.assertFalse(result.ok, result.as_dict())
        self.assertIn('stopped before drawing', result.stop_message())

    def test_blank_or_weak_edges_fall_back_to_canvas_guard(self):
        image = Image.new('RGB', (120, 100), (255, 255, 255))
        result = verify_canvas_edges(image, (10, 10, 80, 60), tolerance_px=4)
        self.assertTrue(result.ok, result.as_dict())
        self.assertEqual(result.detected_sides, 0)
        self.assertIn('Canvas Guard fallback', result.describe())

    def test_capture_tuple_adapter(self):
        image = Image.new('RGB', (100, 80), (190, 190, 190))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 8, 91, 71), fill=(250, 250, 250))
        result = verify_canvas_edges_from_capture((image, (8, 8, 84, 64), (0, 0, 100, 80)))
        self.assertTrue(result.ok, result.as_dict())


if __name__ == '__main__':
    unittest.main()
