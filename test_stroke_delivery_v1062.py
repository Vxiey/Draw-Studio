import unittest
from unittest.mock import patch

from StrokeDelivery import resolve_stroke_delivery
from WindowsMouse import WindowsMouse
from Version import APP_VERSION, FILE_VERSION


class StrokeDeliveryV1063Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(APP_VERSION, '1.0.124-beta')
        self.assertEqual(FILE_VERSION, '1.0.124')

    def test_paint_auto_uses_compatible_adaptive_policy(self):
        policy=resolve_stroke_delivery({'profile_name':'Microsoft Paint','stroke_step_px':8},dry_run=False)
        self.assertEqual(policy.step_px,4.0)
        self.assertGreaterEqual(policy.min_path_delay,0.002)
        self.assertGreater(policy.press_settle,0)
        self.assertGreater(policy.release_settle,0)
        self.assertEqual(policy.drag_backend,'cursor')
        self.assertFalse(policy.native_drag_reliability)

    def test_explicit_reliable_mode_remains_available(self):
        policy=resolve_stroke_delivery({'profile_name':'Microsoft Paint','stroke_step_px':8,'paint_stroke_delivery':'Reliable'},dry_run=False)
        self.assertEqual(policy.drag_backend,'sendinput')
        self.assertTrue(policy.native_drag_reliability)
        self.assertLessEqual(policy.step_px,3.0)

    def test_dry_run_does_not_change_cursor_sampling_policy(self):
        policy=resolve_stroke_delivery({'profile_name':'Microsoft Paint','stroke_step_px':8},dry_run=True)
        self.assertEqual(policy.step_px,8.0)
        self.assertEqual(policy.drag_backend,'cursor')

    def test_held_mouse_defaults_to_compatible_cursor_backend(self):
        mouse=WindowsMouse.__new__(WindowsMouse)
        mouse._input_armed=True;mouse.held=True;mouse.drag_backend='cursor'
        mouse.position_tolerance=0;mouse.position_attempts=2;mouse.position_retry_after=0
        mouse.get_position=lambda:(100,100);mouse.desktop_rect=lambda:(0,0,1920,1080);mouse.buttons_down=lambda:()
        sent=[];mouse._send_absolute_move=lambda x,y:sent.append((x,y))
        class Api:
            def SetCursorPos(self,x,y):return 1
        mouse.api=Api()
        with patch('WindowsMouse.time.sleep'), patch('WindowsMouse.ctypes.set_last_error', create=True):
            mouse.move(100,100)
        self.assertEqual(sent,[])

if __name__=='__main__':unittest.main()
