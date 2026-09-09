import unittest
from PIL import Image, ImageDraw
from BrowserAutoCalibration import detect_browser_canvas
from GarticEngineV2 import detect_gartic_canvas
from EdgeDetection import verify_canvas_edges


class GarticCanvasEdgeCalibrationTests(unittest.TestCase):
    def scene(self):
        image = Image.new('RGB', (1200, 800), (96, 40, 155))
        ImageDraw.Draw(image).rectangle((100, 100, 999, 599), fill='white')
        return image

    def test_connected_paper_extension_is_removed_before_planning(self):
        image = self.scene()
        # A small connected white decoration extends the component bounding
        # box six pixels beyond the dominant right edge.
        ImageDraw.Draw(image).rectangle((1000, 570, 1005, 599), fill='white')
        raw = detect_gartic_canvas(image).box
        self.assertIsNotNone(raw)
        l,t,r,b = raw
        self.assertFalse(verify_canvas_edges(image, (l,t,r-l,b-t)).ok)
        box = detect_browser_canvas('gartic-phone', image)['canvas_box']
        self.assertEqual(box, (100, 100, 1000, 600))
        l,t,r,b = box
        self.assertTrue(verify_canvas_edges(image, (l,t,r-l,b-t)).ok)

    def test_clean_canvas_keeps_bounds(self):
        self.assertEqual(detect_browser_canvas('gartic-phone', self.scene())['canvas_box'],
                         (100,100,1000,600))

    def test_manual_oversized_selection_still_stops(self):
        self.assertFalse(verify_canvas_edges(self.scene(), (100,100,906,500)).ok)

    def test_screen_origin_applied_after_refinement(self):
        box = detect_browser_canvas('gartic-phone', self.scene(), screen_origin=(-1200,50))['canvas_box']
        self.assertEqual(box, (-1100,150,-200,650))

    def test_previous_layout_cache_is_not_reused(self):
        import json
        import tempfile
        from pathlib import Path
        from LayoutFingerprintV2 import load_cache
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cache.json'
            path.write_text(json.dumps({'version': 2, 'entries': [{'profile_key': 'gartic-phone'}]}))
            self.assertEqual(load_cache(path)['entries'], [])
