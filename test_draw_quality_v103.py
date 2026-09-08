import unittest
from types import SimpleNamespace

from PIL import Image, ImageDraw

from LocalSanitization import safe_context
from DrawBot import DrawBotApp, make_plan
from PortraitPlanner import prepare_portrait_image, portrait_sample_limit, portrait_strokes


class Value:
    def __init__(self, value): self.value=value
    def get(self): return self.value


def base_options(**changes):
    data=dict(detail=8,delay=.01,precision='High',lines=True,skip_white=True,
              contrast=1.0,outline=False,brush_px=1,max_seconds=240,
              paint_current_color=True,erase_mode=False,render_style='Portrait / shaded',
              portrait_focus=True,draw_quality='High likeness')
    data.update(changes)
    return data


class DrawQualityV103Tests(unittest.TestCase):
    def setUp(self):
        self.face=Image.new('RGB',(320,240),(205,210,215))
        d=ImageDraw.Draw(self.face)
        d.rectangle((0,0,319,239),fill=(145,155,165))
        d.ellipse((88,22,232,222),fill=(205,178,152))
        d.pieslice((82,10,238,108),180,360,fill=(50,48,45))
        d.ellipse((120,96,138,110),fill=(30,28,25))
        d.ellipse((182,96,200,110),fill=(30,28,25))
        d.line((160,110,154,158),fill=(105,75,65),width=4)
        d.arc((132,148,190,183),15,165,fill=(72,42,38),width=4)

    def test_quality_increases_analysis_resolution(self):
        b=portrait_sample_limit(9,'Balanced')
        h=portrait_sample_limit(9,'High likeness')
        m=portrait_sample_limit(9,'Maximum likeness')
        self.assertLess(b,h); self.assertLess(h,m)

    def test_high_likeness_reports_priority_strokes(self):
        gray,_=prepare_portrait_image(self.face,(800,600),8,draw_quality='High likeness')
        _,stats=portrait_strokes(gray,8,True,max_strokes=500,draw_quality='High likeness')
        self.assertEqual(stats.draw_quality,'High likeness')
        self.assertGreater(stats.priority_strokes,0)
        self.assertLessEqual(stats.priority_strokes,stats.tone_strokes)

    def test_maximum_likeness_limits_long_tone_runs(self):
        gray=Image.new('L',(180,70),50)
        groups,_=portrait_strokes(gray,9,True,include_edges=False,max_strokes=2000,
                                  draw_quality='Maximum likeness',subject_focus=False)
        lengths=[max(abs(x2-x1),abs(y2-y1))+1 for x1,y1,x2,y2 in groups[0]]
        self.assertTrue(lengths)
        self.assertLessEqual(max(lengths),16)

    def test_balanced_can_keep_longer_tone_runs(self):
        gray=Image.new('L',(180,70),50)
        groups,_=portrait_strokes(gray,9,True,include_edges=False,max_strokes=2000,
                                  draw_quality='Balanced',subject_focus=False)
        lengths=[max(abs(x2-x1),abs(y2-y1))+1 for x1,y1,x2,y2 in groups[0]]
        self.assertGreater(max(lengths),16)

    def test_make_plan_carries_quality_stats(self):
        plan=make_plan(self.face,(800,600),base_options(draw_quality='Maximum likeness'))
        stats=plan['options']['portrait_stats']
        self.assertEqual(stats['draw_quality'],'Maximum likeness')
        self.assertGreater(stats['priority_strokes'],0)
        self.assertGreater(stats['sample_size'][0],0)

    def test_maximum_plan_uses_larger_sample_than_balanced(self):
        balanced=make_plan(self.face,(800,600),base_options(draw_quality='Balanced',max_seconds=300))
        maximum=make_plan(self.face,(800,600),base_options(draw_quality='Maximum likeness',max_seconds=300))
        self.assertGreater(maximum['options']['portrait_stats']['sample_size'][0],
                           balanced['options']['portrait_stats']['sample_size'][0])

    def test_invalid_draw_quality_is_rejected(self):
        with self.assertRaises(ValueError):
            prepare_portrait_image(self.face,(800,600),8,draw_quality='Impossible')

    def test_options_falls_back_to_high_likeness_for_old_test_objects(self):
        app=SimpleNamespace(
            brush_px=Value('2'),max_seconds=Value('180'),quality=Value('Balanced'),
            speed=Value('Normal'),precision=Value('High'),mode=Value('Lines (fastest)'),
            render_style=Value('Auto'),game=Value('Other drawing app'),paint_tool=Value('Use current tool'),
            contrast=Value(1.0),portrait_focus=Value(True),skip_white=Value(True),outline=Value(False),
        )
        result=DrawBotApp.options(app)
        self.assertEqual(result['draw_quality'],'High likeness')

    def test_bug_report_context_allows_draw_quality(self):
        cleaned=safe_context({'draw_quality':'Maximum likeness','secret':'no'})
        self.assertEqual(cleaned['draw_quality'],'Maximum likeness')
        self.assertNotIn('secret',cleaned)


if __name__=='__main__':
    unittest.main()
