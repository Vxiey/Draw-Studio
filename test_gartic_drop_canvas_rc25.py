import base64
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image,ImageDraw

from CanvasDropPayload import parse_canvas_drop
from DrawBot import DrawBotApp,load_image
from GarticEngineV2 import detect_gartic_canvas


class Value:
    def __init__(self,value=None):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


class GarticDropCanvasRc25Tests(unittest.TestCase):
    def test_google_data_image_payload_is_accepted(self):
        payload='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
        result=parse_canvas_drop('<img src="'+payload+'">')
        self.assertEqual(result.kind,'data');self.assertEqual(result.source,payload)

    def test_data_image_loader_is_bounded_and_decodes(self):
        payload='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
        image=load_image(payload)
        self.assertEqual(image.size,(1,1))

    def test_correct_canvas_beats_larger_white_ui_panel(self):
        image=Image.new('RGB',(1400,900),(96,40,155));d=ImageDraw.Draw(image)
        d.rectangle((20,20,1370,210),fill='white')
        d.rectangle((300,250,1199,749),fill='white')
        result=detect_gartic_canvas(image)
        self.assertTrue(result.found);self.assertEqual(result.box,(300,250,1200,750))

    def test_partly_drawn_canvas_uses_frame_fallback(self):
        image=Image.new('RGB',(1400,900),(96,40,155));d=ImageDraw.Draw(image)
        d.rectangle((300,250,1199,749),fill=(218,218,218))
        for x in range(320,1180,48):d.rectangle((x,270,x+20,730),fill=(30,100,180))
        result=detect_gartic_canvas(image)
        self.assertTrue(result.found);self.assertEqual(result.box,(300,250,1200,750))
        self.assertIn('structural frame',result.reason)

    def test_f1_uses_normal_guard_then_unlock_and_start(self):
        app=SimpleNamespace(activity=None,closing=False,quick_start_last_monotonic=0.0,game=Value('Gartic Phone'),status=Value(''))
        with mock.patch.object(DrawBotApp,'_start_guard_ready',return_value=(True,'Basic setup ready.')),\
             mock.patch.object(DrawBotApp,'_full_draw_unlocked',return_value=False),\
             mock.patch.object(DrawBotApp,'unlock_full_drawing',return_value=True) as unlock,\
             mock.patch.object(DrawBotApp,'start_full_drawing',return_value=True) as start:
            self.assertTrue(DrawBotApp.quick_start_hotkey(app))
        unlock.assert_called_once_with(app);start.assert_called_once_with(app)


class GarticDirectDropArmRc25Tests(unittest.TestCase):
    def test_arm_drop_in_can_discover_gartic_before_palette_setup(self):
        callback=mock.Mock(return_value=True)
        app=SimpleNamespace(activity=None,closing=False,game=Value('Gartic Phone'),status=Value(''),arm_smart_canvas_drop=callback)
        with mock.patch.object(DrawBotApp,'_start_guard_ready',return_value=(False,'Start locked: select the drawing area first.')):
            self.assertTrue(DrawBotApp.arm_manual_drop_in(app))
        callback.assert_called_once_with()

if __name__=='__main__':unittest.main()
