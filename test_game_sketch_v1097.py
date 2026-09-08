import unittest,threading
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from DrawBot import uses_paint_color,bypasses_palette,DrawBotApp,make_plan,execute_plan
from BrowserVisualPreflight import verify_browser_visual_preflight
from test_drawbot import Mouse,NoWait,options

class GameSketchTests(unittest.TestCase):
    def app(self,name,on=True):
        a=SimpleNamespace(game=Mock(),paint_simple=Mock(),outline=Mock(),subject_focus=Mock(),brush_px=Mock(),status=Mock(),_schedule_paint_configuration_refresh=Mock())
        a.game.get.return_value=name;a.paint_simple.get.return_value=on
        return a
    def test_gartic_profiles_can_use_current_ink(self):
        for name in ('Gartic.io','Gartic Phone','Skribbl.io','Microsoft Paint'):
            self.assertTrue(bypasses_palette(self.app(name)))
            self.assertFalse(bypasses_palette(self.app(name,False)))
    def test_toggle_enables_contours_without_input(self):
        a=self.app('Gartic Phone');DrawBotApp.paint_mode_changed(a)
        a.outline.set.assert_called_once_with(True)
        a.subject_focus.set.assert_called_once_with('Off')
        a._schedule_paint_configuration_refresh.assert_called_once()
    def test_contour_execution_never_selects_palette(self):
        im=Image.new('RGB',(60,60),'white');ImageDraw.Draw(im).rectangle((10,10,40,40),fill='red')
        plan=make_plan(im,(100,100),dict(options(),outline=True,paint_current_color=True,brush_px=1))
        m=Mouse();execute_plan(plan,(100,100,100,100),(),m,NoWait(),threading.Event(),lambda *a:None)
        self.assertGreater(plan['count'],0)
        self.assertFalse(any(a[0]=='click' for a in m.actions))
        self.assertTrue(any(a[0]=='press' for a in m.actions))
        self.assertFalse(m.held)
    def preflight(self,box,confidence=.9,require=False):
        with patch('BrowserVisualPreflight.detect_browser_canvas',return_value={'canvas_box':box,'canvas_confidence':confidence}),patch('BrowserVisualPreflight.detect_browser_setup',return_value={'canvas_box':box,'canvas_confidence':confidence}):
            return verify_browser_visual_preflight('gartic-phone',{'client_rect':(0,0,400,300)},(20,20,380,280),(),screenshot=Image.new('RGB',(400,300),'white'),require_palette=require)
    def test_canvas_only_does_not_require_palette(self):
        r=self.preflight((20,20,380,280));self.assertTrue(r.passed);self.assertEqual(r.palette_tested,0)
    def test_canvas_only_still_rejects_moved_or_missing_canvas(self):
        for box in (None,(40,20,400,280)):
            self.assertFalse(self.preflight(box).passed)
        self.assertFalse(self.preflight((20,20,380,280),.4).passed)
    def test_colour_mode_still_requires_palette(self):
        self.assertFalse(self.preflight((20,20,380,280),require=True).passed)
