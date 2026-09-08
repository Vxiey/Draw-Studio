import unittest
from unittest.mock import patch

from DrawBot import DrawBotApp
from ScreenGuard import GuardedMouse
from test_drawbot import Mouse


class TargetRebaseTests(unittest.TestCase):
    def app(self):
        app=DrawBotApp.__new__(DrawBotApp)
        app.target_window=(123,(0,0,1016,739))
        app.target_client_rect=(8,31,1008,731)
        app.corners=[(100,200),(600,500)]
        app.saved_area=[(100,200),(600,500)]
        return app

    def test_same_size_window_move_rebases_area(self):
        app=self.app()
        meta={'handle':123,'rect':(20,10,1036,749),'client_rect':(28,41,1028,741),'target_pid':1}
        with patch('TargetCapture.probe_handle_isolated',return_value=meta):
            current=DrawBotApp._refresh_target_for_draw(app)
        self.assertEqual(current,(28,41,1028,741))
        self.assertEqual(app.corners,[(120,210),(620,510)])
        self.assertEqual(app.target_window,(123,(20,10,1036,749)))

    def test_resize_stops_before_rebase(self):
        app=self.app()
        meta={'handle':123,'rect':(0,0,1216,839),'client_rect':(8,31,1208,831),'target_pid':1}
        with patch('TargetCapture.probe_handle_isolated',return_value=meta):
            with self.assertRaisesRegex(ValueError,'changed size'):
                DrawBotApp._refresh_target_for_draw(app)
        self.assertEqual(app.corners,[(100,200),(600,500)])


class PalettePreflightTests(unittest.TestCase):
    def test_palette_mismatch_happens_before_mouse_move(self):
        class Monitor:
            def rectangle(self,handle):return (0,0,800,600)
            def color(self,point):return (255,255,255)
        mouse=Mouse();guard=GuardedMouse(mouse,Monitor(),(1,(0,0,800,600)),{(50,50):(0,0,0)})
        with self.assertRaisesRegex(InterruptedError,'No mouse input was sent'):
            guard.verify_palette_layout()
        self.assertEqual(mouse.actions,[])

    def test_matching_palette_is_verified_once(self):
        class Monitor:
            def __init__(self):self.reads=0
            def rectangle(self,handle):return (0,0,800,600)
            def color(self,point):self.reads+=1;return (10,20,30)
        monitor=Monitor();guard=GuardedMouse(Mouse(),Monitor(),(1,(0,0,800,600)),{(50,50):(10,20,30)})
        guard.verify_palette_layout();guard.verify_palette_layout()
        self.assertTrue(guard.palette_verified)


if __name__=='__main__':unittest.main()
