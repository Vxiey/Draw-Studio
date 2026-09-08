import unittest
from collections import Counter
from types import SimpleNamespace

from LocalSanitization import safe_context
from DrawBot import DrawBotApp, finish_plan
from HumanMode import (HUMAN_MODES, HumanCadence, human_overhead_seconds,
                       humanize_strokes, stable_seed, validate_human_mode)
from PIL import Image


class Value:
    def __init__(self, value): self.value=value
    def get(self): return self.value


def undirected(stroke):
    x1,y1,x2,y2=stroke
    a,b=(x1,y1),(x2,y2)
    return (a,b) if a<=b else (b,a)


class HumanModeV104Tests(unittest.TestCase):
    def setUp(self):
        self.strokes=[(i, i%7, i+4, (i+3)%7) for i in range(80)]

    def test_modes_are_explicit(self):
        self.assertEqual(HUMAN_MODES,('Off','Subtle','Natural','Strong'))
        for mode in HUMAN_MODES:self.assertEqual(validate_human_mode(mode),mode)
        with self.assertRaises(ValueError):validate_human_mode('Stealth')

    def test_off_is_geometry_and_order_identical(self):
        self.assertEqual(humanize_strokes(self.strokes,'Off',123),self.strokes)

    def test_natural_preserves_exact_undirected_geometry(self):
        out=humanize_strokes(self.strokes,'Natural',123)
        self.assertEqual(Counter(map(undirected,out)),Counter(map(undirected,self.strokes)))
        self.assertNotEqual(out,self.strokes)

    def test_humanization_is_deterministic_for_same_seed(self):
        self.assertEqual(humanize_strokes(self.strokes,'Strong',987),
                         humanize_strokes(self.strokes,'Strong',987))

    def test_seed_does_not_need_image_path(self):
        groups=[self.strokes[:20],self.strokes[20:]]
        self.assertEqual(stable_seed(groups,'Subtle'),stable_seed(groups,'Subtle'))
        self.assertNotEqual(stable_seed(groups,'Subtle'),stable_seed(groups,'Natural'))

    def test_cadence_off_returns_base_delay_and_no_pause(self):
        c=HumanCadence('Off',1)
        self.assertEqual(c.movement_delay(.01,2,10),.01)
        self.assertEqual(c.boundary_pause(1000),0)

    def test_natural_cadence_stays_bounded(self):
        c=HumanCadence('Natural',4)
        samples=[c.movement_delay(.01,i,20) for i in range(20)]
        self.assertTrue(all(.0055 <= v <= .0155 for v in samples))
        self.assertGreater(max(samples),min(samples))

    def test_human_overhead_is_monotonic_enough_for_eta(self):
        self.assertEqual(human_overhead_seconds(500,'Off'),0)
        self.assertGreater(human_overhead_seconds(500,'Subtle'),0)
        self.assertGreater(human_overhead_seconds(500,'Natural'),human_overhead_seconds(500,'Subtle'))
        self.assertGreater(human_overhead_seconds(500,'Strong'),human_overhead_seconds(500,'Natural'))

    def test_finish_plan_eta_includes_human_overhead(self):
        image=Image.new('RGBA',(100,100),'white')
        groups=[self.strokes[:30]]
        common=dict(delay=.01,precision='High',paint_current_color=True,erase_mode=False,
                    brush_px=1,max_seconds=180)
        off=finish_plan(image,(400,400),groups,dict(common,human_mode='Off'))
        natural=finish_plan(image,(400,400),groups,dict(common,human_mode='Natural'))
        self.assertGreater(natural['estimate'],off['estimate'])

    def test_options_falls_back_to_subtle_for_old_objects(self):
        app=SimpleNamespace(
            brush_px=Value('2'),max_seconds=Value('180'),quality=Value('Balanced'),
            speed=Value('Normal'),precision=Value('High'),mode=Value('Lines (fastest)'),
            render_style=Value('Auto'),draw_quality=Value('High likeness'),
            game=Value('Other drawing app'),paint_tool=Value('Use current tool'),
            contrast=Value(1.0),portrait_focus=Value(True),skip_white=Value(True),outline=Value(False),
        )
        result=DrawBotApp.options(app)
        self.assertEqual(result['human_mode'],'Off')

    def test_bug_report_context_allows_human_mode(self):
        cleaned=safe_context({'human_mode':'Natural','secret':'no'})
        self.assertEqual(cleaned['human_mode'],'Natural')
        self.assertNotIn('secret',cleaned)


if __name__=='__main__':unittest.main()
