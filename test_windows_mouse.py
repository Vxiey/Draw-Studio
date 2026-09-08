import ctypes
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from WindowsMouse import WindowsMouse,Input,normalize_position
from GameProfiles import PROFILES,add_custom_profile,load_custom_profiles

class NativeMouseTests(unittest.TestCase):
    def test_input_size_matches_windows_pointer_width(self):
        self.assertEqual(ctypes.sizeof(Input),40 if ctypes.sizeof(ctypes.c_void_p)==8 else 28)

    def test_virtual_desktop_coordinates(self):
        self.assertEqual(normalize_position(-1920,0,(-1920,0,3840,1080)),(0,0))
        self.assertEqual(normalize_position(1919,1079,(-1920,0,3840,1080)),(65535,65535))
        with self.assertRaises(ValueError):normalize_position(1920,0,(-1920,0,3840,1080))

    def test_movement_uses_set_cursor_pos_and_must_be_observed(self):
        mouse=WindowsMouse.__new__(WindowsMouse)
        class Api:
            def GetSystemMetrics(self,i):return {76:0,77:0,78:1920,79:1080}[i]
            def SetCursorPos(self,x,y):return 1
        mouse.api=Api();mouse.get_position=lambda:(0,0);mouse._input_armed=True;mouse.held=False;mouse.buttons_down=lambda:()
        with patch('WindowsMouse.ctypes.set_last_error',create=True), patch('WindowsMouse.time.sleep'):
            with self.assertRaisesRegex(OSError,'did not reach'):mouse.move(100,100)

    def test_set_cursor_pos_failure_reported(self):
        mouse=WindowsMouse.__new__(WindowsMouse)
        class Api:
            def GetSystemMetrics(self,i):return {76:0,77:0,78:1920,79:1080}[i]
            def SetCursorPos(self,x,y):return 0
        mouse.api=Api();mouse._input_armed=True;mouse.held=False;mouse.buttons_down=lambda:()
        with patch('WindowsMouse.ctypes.set_last_error',create=True), patch('WindowsMouse.ctypes.get_last_error',return_value=5,create=True):
            with self.assertRaisesRegex(OSError,'code 5'):mouse.move(100,100)

    def test_sendinput_failure_reported(self):
        mouse=WindowsMouse.__new__(WindowsMouse)
        class Api:
            def SendInput(self,*args):return 0
        mouse.api=Api()
        with patch('WindowsMouse.ctypes.set_last_error',create=True), patch('WindowsMouse.ctypes.get_last_error',return_value=5,create=True):
            with self.assertRaisesRegex(OSError,'code 5'):mouse._send(1)

    def test_release_only_own_press(self):
        mouse=WindowsMouse.__new__(WindowsMouse);mouse.held=False;mouse._input_armed=True;sent=[];mouse._send=lambda flags:sent.append(flags);mouse.buttons_down=lambda:()
        mouse.release();self.assertEqual(sent,[])
        mouse.press();mouse.release();mouse.release();self.assertEqual(sent,[2,4])

    def test_arm_input_rejects_existing_mouse_button(self):
        mouse=WindowsMouse.__new__(WindowsMouse);mouse.held=False;mouse._input_armed=False
        mouse.buttons_down=lambda:('left',)
        with self.assertRaisesRegex(InterruptedError,'Release all mouse buttons'):
            mouse.arm_input()
        self.assertFalse(mouse.input_armed)

    def test_mouse_input_is_disarmed_by_default(self):
        mouse=WindowsMouse.__new__(WindowsMouse);mouse.held=False
        class Api:
            def GetSystemMetrics(self,index):return {76:0,77:0,78:1920,79:1080}[index]
            def SetCursorPos(self,x,y):return 1
        mouse.api=Api();mouse.get_position=lambda:(0,0)
        with self.assertRaisesRegex(PermissionError,'locked'):mouse.move(100,100)
        with self.assertRaisesRegex(PermissionError,'locked'):mouse.press()

    def test_custom_profiles_survive_reload_and_use_safe_keys(self):
        old=dict(PROFILES)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'profiles.json';add_custom_profile('Mitt program',path)
                key=PROFILES.pop('Mitt program')[0];load_custom_profiles(path)
                self.assertEqual(PROFILES['Mitt program'][0],key);self.assertTrue(key.startswith('custom-'))
                with self.assertRaises(ValueError):add_custom_profile('Mitt program',path)
        finally:PROFILES.clear();PROFILES.update(old)

if __name__=='__main__':unittest.main()
