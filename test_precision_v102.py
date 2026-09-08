import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from Precision import (CanvasTransform, effective_step, map_pixel_center,
                       precision_path, round_screen)
from DrawBot import DrawBotApp, execute_plan


class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


class PrecisionMathTests(unittest.TestCase):
    def test_identity_mapping_has_no_half_pixel_bias(self):
        transform=CanvasTransform(100,80,(100,80),10,20)
        self.assertEqual(transform.point(0,0),(10,20))
        self.assertEqual(transform.point(99,79),(109,99))
        self.assertEqual(map_pixel_center(0,100,100,10),10.0)

    def test_round_screen_does_not_use_bankers_rounding(self):
        self.assertEqual(round_screen(.5),1)
        self.assertEqual(round_screen(2.5),3)
        self.assertEqual(round_screen(-.5),-1)
        self.assertEqual(round_screen(-2.5),-3)

    def test_precision_step_caps_requested_density(self):
        self.assertEqual(effective_step('Normal',12),12)
        self.assertEqual(effective_step('High',12),4)
        self.assertEqual(effective_step('Ultra',12),2)

    def test_diagonal_uses_euclidean_spacing_and_exact_endpoint(self):
        high=precision_path((0,0),(20,20),'High',12)
        ultra=precision_path((0,0),(20,20),'Ultra',12)
        self.assertEqual(high[-1],(20,20))
        self.assertEqual(ultra[-1],(20,20))
        self.assertGreater(len(ultra),len(high))
        for path,max_step in ((high,4.0),(ultra,2.0)):
            previous=(0,0)
            for point in path:
                # Integer rounding can add <1 pixel to the continuous target,
                # but no large sparse jumps are allowed.
                self.assertLessEqual(math.hypot(point[0]-previous[0],point[1]-previous[1]),max_step+1.5)
                previous=point

    def test_paths_do_not_repeat_same_integer_coordinate(self):
        path=precision_path((0,0),(7,1),'Ultra',8)
        self.assertEqual(len(path),len(set(path)))
        self.assertEqual(path[-1],(7,1))


class PrecisionSettingsTests(unittest.TestCase):
    def test_options_include_precision(self):
        app=SimpleNamespace(
            brush_px=Value('2'),max_seconds=Value('180'),quality=Value('Balanced'),
            speed=Value('Normal'),precision=Value('Ultra'),mode=Value('Lines (fastest)'),
            render_style=Value('Auto'),game=Value('Other drawing app'),paint_tool=Value('Use current tool'),
            contrast=Value(1.0),portrait_focus=Value(True),skip_white=Value(True),outline=Value(False),
            paint_simple=Value(False))
        options=DrawBotApp.options(app)
        self.assertEqual(options['precision'],'Ultra')

    def test_invalid_precision_is_rejected(self):
        app=SimpleNamespace(
            brush_px=Value('2'),max_seconds=Value('180'),quality=Value('Balanced'),
            speed=Value('Normal'),precision=Value('Impossible'),mode=Value('Lines (fastest)'),
            render_style=Value('Auto'),game=Value('Other drawing app'),paint_tool=Value('Use current tool'),
            contrast=Value(1.0),portrait_focus=Value(True),skip_white=Value(True),outline=Value(False),
            paint_simple=Value(False))
        with self.assertRaisesRegex(ValueError,'precision'):
            DrawBotApp.options(app)


class DpiSafetyTests(unittest.TestCase):
    def test_dpi_change_stops_before_rebase(self):
        app=DrawBotApp.__new__(DrawBotApp)
        app.target_window=(123,(0,0,1000,700));app.target_client_rect=(0,0,1000,700)
        app.target_dpi=96;app.corners=[(100,100),(500,400)]
        meta={'handle':123,'rect':(0,0,1000,700),'client_rect':(0,0,1000,700),'dpi':144,'target_pid':1}
        with patch('TargetCapture.probe_handle_isolated',return_value=meta):
            with self.assertRaisesRegex(ValueError,'DPI changed'):
                DrawBotApp._refresh_target_for_draw(app)
        self.assertEqual(app.corners,[(100,100),(500,400)])


class PrecisionMouseConfigurationTests(unittest.TestCase):
    def test_windows_mouse_high_requires_exact_position(self):
        from WindowsMouse import WindowsMouse
        mouse=WindowsMouse.__new__(WindowsMouse)
        mouse.held=False;mouse._input_armed=True;mouse.buttons_down=lambda:()
        class Api:
            def __init__(self):self.calls=[]
            def GetSystemMetrics(self,index):return {76:0,77:0,78:1920,79:1080}[index]
            def SetCursorPos(self,x,y):self.calls.append((x,y));return 1
        api=Api();mouse.api=api
        positions=iter([(99,100),(99,100),(100,100)])
        mouse.get_position=lambda:next(positions,(100,100))
        mouse.configure_precision('High')
        with patch('WindowsMouse.ctypes.set_last_error',create=True), patch('WindowsMouse.time.sleep'):
            mouse.move(100,100)
        self.assertEqual(mouse.position_tolerance,0)
        self.assertGreaterEqual(len(api.calls),1)

    def test_normal_allows_one_pixel_observation_tolerance(self):
        from WindowsMouse import WindowsMouse
        mouse=WindowsMouse.__new__(WindowsMouse)
        mouse.held=False;mouse._input_armed=True;mouse.buttons_down=lambda:()
        class Api:
            def GetSystemMetrics(self,index):return {76:0,77:0,78:1920,79:1080}[index]
            def SetCursorPos(self,x,y):return 1
        mouse.api=Api();mouse.get_position=lambda:(99,100);mouse.configure_precision('Normal')
        with patch('WindowsMouse.ctypes.set_last_error',create=True):
            mouse.move(100,100)
        self.assertEqual(mouse.position_tolerance,1)


if __name__=='__main__':
    unittest.main()
