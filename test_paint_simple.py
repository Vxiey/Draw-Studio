import threading
import unittest
from PIL import Image
from DrawBot import make_plan,make_test_plan,execute_plan,uses_paint_color
from PixelData import monochrome_strokes
from test_drawbot import Mouse,NoWait,options
from types import SimpleNamespace

class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value

class SimplePaintTests(unittest.TestCase):
    def test_no_palette_clicks_and_no_assumed_ink_color(self):
        plan=make_test_plan((180,135),dict(options(),paint_current_color=True))
        mouse=Mouse();mouse.verify_ink=lambda *args:self.fail('Selected Paint color is unknown')
        execute_plan(plan,(100,100,180,135),(),mouse,NoWait(),threading.Event(),lambda *args:None)
        self.assertEqual(plan['count'],1)
        self.assertFalse(any(action[0]=='click' for action in mouse.actions))
        self.assertTrue(any(action[0]=='press' for action in mouse.actions))
        self.assertFalse(mouse.held)
    def test_white_and_transparent_pixels_are_not_filled(self):
        image=Image.new('RGBA',(5,1),'white')
        image.putpixel((0,0),(0,0,0,255));image.putpixel((2,0),(0,0,0,0));image.putpixel((4,0),(0,0,0,255))
        self.assertEqual(monochrome_strokes(image),[[(0,0,0,0),(4,0,4,0)]])
    def test_plan_has_single_black_preview_color(self):
        plan=make_plan(Image.new('RGBA',(8,4),'black'),(80,40),dict(options(),paint_current_color=True))
        self.assertEqual(plan['colors'],((0,0,0),));self.assertEqual(len(plan['groups']),1)
        self.assertGreater(plan['count'],0)
    def test_current_ink_enabled_for_game_profiles(self):
        self.assertTrue(uses_paint_color(SimpleNamespace(game=Value('Microsoft Paint'),paint_simple=Value(True))))
        self.assertTrue(uses_paint_color(SimpleNamespace(game=Value('Skribbl.io'),paint_simple=Value(True))))
        self.assertFalse(uses_paint_color(SimpleNamespace(game=Value('Microsoft Paint'),paint_simple=Value(False))))
    def test_cancelled_preparation_does_not_continue(self):
        with self.assertRaises(InterruptedError):monochrome_strokes(Image.new('RGBA',(10,10),'black'),cancelled=lambda:True)

if __name__=='__main__':unittest.main()
