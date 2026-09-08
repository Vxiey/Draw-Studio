import threading
import unittest
from PIL import Image

from CanvasGuard import CanvasGuard, CanvasModel, CanvasSafetyStop, FinalMouseGuard, point_in_polygon
from DrawBot import execute_plan


class Stop:
    def is_set(self): return False
    def wait(self, seconds): return False


class Mouse:
    def __init__(self):
        self.position=(0,0);self.held=False;self.actions=[]
    def get_position(self): return self.position
    def move(self,x,y):
        self.position=(int(x),int(y));self.actions.append(('move',int(x),int(y)))
    def click(self): self.actions.append(('click',))
    def press(self): self.held=True;self.actions.append(('press',))
    def release(self): self.held=False;self.actions.append(('release',))


def base_plan():
    return {
        'image': Image.new('RGBA',(10,10),'black'),
        'fitted': (10,10),
        'groups': [[(0,5,9,5)]],
        'execution_groups': None,
        'execution_sequence': [],
        'count': 1,
        'options': {'delay':0,'max_seconds':30,'precision':'Normal','speed':'Fast','brush_px':3,
                    'paint_current_color':False,'strict_color_verification':False},
        'colors': ((0,0,0),),
        'color_selectors': ({'kind':'palette','palette_index':0},),
    }


class CanvasGuardV1047Tests(unittest.TestCase):
    def test_safe_polygon_insets_brush(self):
        model=CanvasModel.from_area((100,200,50,30),brush_px=5,edge_margin_px=2)
        self.assertEqual(model.brush_inset.radius_px,3)
        self.assertEqual(model.brush_inset.total_px,5)
        self.assertEqual(model.safe_bounds,(105,205,144,224))
        self.assertTrue(point_in_polygon((105,205),model.safe_polygon))
        self.assertFalse(point_in_polygon((101,205),model.safe_polygon))

    def test_final_mouse_guard_clamps_edge_points_before_input(self):
        raw=Mouse();guard=FinalMouseGuard(raw,CanvasGuard.from_area((100,100,20,20),brush_px=3,edge_margin_px=2))
        safe=guard.move(100,100)
        self.assertEqual(safe,(104,104))
        self.assertEqual(raw.position,(104,104))
        guard.press();guard.release()
        self.assertFalse(raw.held)

    def test_canvas_guard_rejects_points_outside_canvas(self):
        guard=CanvasGuard.from_area((100,100,20,20),brush_px=3,edge_margin_px=2)
        with self.assertRaises(CanvasSafetyStop):
            guard.protect_point((99,110),'outside test')

    def test_execute_plan_draw_points_are_brush_inset_guarded(self):
        plan=base_plan();mouse=Mouse();events=[]
        execute_plan(plan,(100,100,10,10),[(10,10)],mouse,Stop(),threading.Event(),lambda *e: events.append(e))
        drawing_moves=[a for a in mouse.actions if a[0]=='move' and a[1]>=100 and a[2]>=100]
        self.assertTrue(drawing_moves)
        for _,x,y in drawing_moves:
            self.assertGreaterEqual(x,104);self.assertLessEqual(x,105)
            self.assertGreaterEqual(y,104);self.assertLessEqual(y,105)
        self.assertTrue(plan['options']['canvas_guard_meta']['active'])
        self.assertTrue(any(e[0]=='status' and 'Canvas Guard active' in e[1] for e in events))

    def test_execute_plan_stops_before_canvas_press_when_plan_is_outside(self):
        plan=base_plan();plan['groups']=[ [(-20,0,9,0)] ];mouse=Mouse()
        with self.assertRaises(CanvasSafetyStop):
            execute_plan(plan,(100,100,10,10),[(10,10)],mouse,Stop(),threading.Event(),lambda *e: None)
        self.assertFalse(any(a[0]=='press' for a in mouse.actions))


if __name__=='__main__':unittest.main()
