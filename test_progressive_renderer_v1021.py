import threading
import unittest
from PIL import Image

from DrawBot import make_plan, execute_plan
from ShapePaths import build_shape_execution_paths
from ProgressiveRenderer import build_progressive_sequence, progressive_enabled
from test_drawbot import Mouse, NoWait, options


class ProgressiveRendererTests(unittest.TestCase):
    def test_progressive_sequence_orders_foundation_before_contours_and_details(self):
        groups = [[(0,0,20,0),(0,1,20,1),(5,8,5,10)]]
        execution, meta = build_shape_execution_paths(groups, brush_px=1, order='Contour first', stroke_cap='Unlimited')
        sequence, progressive = build_progressive_sequence(execution, phase_hints=meta['path_phase_hints'], enabled=True)
        self.assertTrue(progressive['progressive_enabled'])
        phases = [entry['phase'] for entry in sequence]
        self.assertLessEqual(max(i for i,p in enumerate(phases) if p == 'foundation'), min(i for i,p in enumerate(phases) if p == 'contour'))
        self.assertEqual(phases[-1], 'details')

    def test_make_plan_adds_sequence_when_progressive_on(self):
        im = Image.new('RGBA', (20, 12), 'white')
        for y in range(0, 8):
            for x in range(0, 16):
                im.putpixel((x,y), (0,0,0,255))
        im.putpixel((19,11), (0,0,0,255))
        opts = dict(options(), drawing_mode='Shape paths', progressive_rendering='On', color_workflow='Progressive passes', shape_order='Fill first', max_stroke_cap='Unlimited', target_stroke_count='Unlimited')
        plan = make_plan(im, (200,120), opts)
        self.assertTrue(plan['execution_sequence'])
        self.assertTrue(plan['path_stats']['progressive_enabled'])
        self.assertEqual(plan['path_stats']['progressive_sequence_paths'], plan['count'])

    def test_execute_uses_progressive_pass_order(self):
        plan = {
            'image': Image.new('RGBA', (10,10), 'black'),
            'fitted': (100,100),
            'groups': [[(0,0,9,0)], [(0,9,9,9)]],
            'execution_groups': [[((0,0),(9,0))], [((0,9),(9,9))]],
            'execution_sequence': [
                {'color_index': 1, 'path': ((0,9),(9,9)), 'phase': 'foundation'},
                {'color_index': 0, 'path': ((0,0),(9,0)), 'phase': 'contour'},
            ],
            'count': 2,
            'estimate': 1,
            'colors': ((0,0,0),(255,0,0)),
            'options': dict(options(), drawing_mode='Shape paths', progressive_rendering='On', speed='Fast', precision='Normal', paint_current_color=False, max_seconds=30),
        }
        mouse = Mouse(); events=[]
        execute_plan(plan, (100,100,100,100), [(10,10),(20,10)], mouse, NoWait(), threading.Event(), lambda *e: events.append(e))
        clicks = [a for a in mouse.actions if a[0] == 'click']
        # Palette click for color 1 must happen before palette click for color 0.
        positions = [(mouse.actions[i-1][1], mouse.actions[i-1][2]) for i,a in enumerate(mouse.actions) if a[0] == 'click']
        self.assertEqual(positions[:2], [(20,10),(10,10)])
        self.assertTrue(any(e[0]=='status' and 'Progressive pass 1/3' in e[1] for e in events))

    def test_auto_progressive_for_shape_or_time_budget(self):
        self.assertTrue(progressive_enabled('Auto', drawing_mode='Shape paths'))
        self.assertTrue(progressive_enabled('Auto', drawing_mode='Smart paths (recommended)', time_budget_active=True))
        self.assertFalse(progressive_enabled('Auto', drawing_mode='Smart paths (recommended)', time_budget_active=False))
        self.assertFalse(progressive_enabled('Off', drawing_mode='Shape paths', time_budget_active=True))


if __name__ == '__main__':
    unittest.main()
