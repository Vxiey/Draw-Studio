import unittest
from PIL import Image, ImageDraw

from DrawBot import make_plan


def opts(**changes):
    values = dict(detail=8, delay=.01, lines=True, skip_white=True, contrast=1.0,
                  outline=False, brush_px=2, max_seconds=180,
                  paint_current_color=True, erase_mode=False,
                  render_style='Auto', portrait_focus=True)
    values.update(changes)
    return values


class PortraitIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Synthetic face-like structure: mid-tone head, dark hair/eyes/mouth and
        # a darker outer background.  Tests planner behaviour, not recognition.
        self.image = Image.new('RGB', (320, 240), (205, 210, 215))
        d = ImageDraw.Draw(self.image)
        d.rectangle((0, 0, 319, 239), fill=(130, 150, 165))
        d.ellipse((85, 25, 235, 220), fill=(205, 175, 150))
        d.pieslice((82, 15, 238, 105), 180, 360, fill=(55, 50, 45))
        d.ellipse((122, 98, 137, 108), fill=(35, 30, 28))
        d.ellipse((183, 98, 198, 108), fill=(35, 30, 28))
        d.line((160, 110, 153, 155), fill=(105, 75, 65), width=4)
        d.arc((132, 145, 190, 185), 15, 165, fill=(75, 45, 40), width=4)

    def test_auto_single_color_uses_portrait_pipeline(self):
        plan = make_plan(self.image, (800, 600), opts())
        self.assertIn('portrait_stats', plan['options'])
        self.assertGreater(plan['options']['portrait_stats']['edge_strokes'], 0)
        self.assertGreater(plan['options']['portrait_stats']['tone_strokes'], 0)

    def test_standard_style_keeps_legacy_single_threshold(self):
        plan = make_plan(self.image, (800, 600), opts(render_style='Standard / pixel'))
        self.assertNotIn('portrait_stats', plan['options'])

    def test_outline_bypasses_shading(self):
        plan = make_plan(self.image, (800, 600), opts(outline=True, render_style='Portrait / shaded'))
        self.assertNotIn('portrait_stats', plan['options'])

    def test_more_time_allows_more_portrait_strokes(self):
        short = make_plan(self.image, (900, 700), opts(max_seconds=120, detail=9))
        long = make_plan(self.image, (900, 700), opts(max_seconds=600, detail=9))
        self.assertGreater(long['count'], short['count'])

    def test_portrait_plan_is_fitted_under_time_limit(self):
        plan = make_plan(self.image, (1200, 900), opts(max_seconds=180, detail=10, delay=.025))
        self.assertLessEqual(plan['estimate'], 180)

    def test_portrait_has_non_horizontal_geometry(self):
        plan = make_plan(self.image, (800, 600), opts(detail=9, max_seconds=400))
        self.assertTrue(any(y1 != y2 for x1, y1, x2, y2 in plan['groups'][0]))


if __name__ == '__main__':
    unittest.main()
