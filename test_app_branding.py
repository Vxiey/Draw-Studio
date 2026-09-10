import sys
import unittest
from pathlib import Path
from PIL import Image
import AppBranding as branding

ROOT = Path(__file__).resolve().parent


class BrandingTests(unittest.TestCase):
    def test_windows_icon_has_small_and_high_dpi_frames(self):
        with Image.open(ROOT / branding.ICON_ICO) as icon:
            self.assertTrue({(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)} <= icon.ico.sizes())
            for size in icon.ico.sizes():
                frame = icon.ico.getimage(size).convert('RGBA')
                self.assertEqual(frame.size, size)
                self.assertLess(frame.getextrema()[3][0], 255)
                self.assertGreater(frame.getextrema()[3][1], 0)
        with Image.open(ROOT / branding.ICON_PNG) as png:
            self.assertEqual(png.size, (512,512))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows Tk identity integration')
    def test_root_dialog_and_header_share_branding(self):
        import customtkinter as ctk
        branding.set_windows_app_id()
        import ctypes
        from ctypes import wintypes
        from unittest.mock import patch
        # Tk does not retain an ICO filename in its X11 bitmap query field.
        # Observe successful native setter calls, then check WM_GETICON instead.
        applied = {}
        def recorder(original):
            def set_icon(window, bitmap=None, default=None):
                result = original(window, bitmap, default)
                applied[window] = bitmap
                return result
            return set_icon
        root_patch = patch.object(ctk.CTk, 'iconbitmap', recorder(ctk.CTk.iconbitmap))
        child_patch = patch.object(ctk.CTkToplevel, 'iconbitmap', recorder(ctk.CTkToplevel.iconbitmap))
        root_patch.start()
        self.addCleanup(root_patch.stop)
        child_patch.start()
        self.addCleanup(child_patch.stop)
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.SendMessageW.restype = ctypes.c_ssize_t
        root=ctk.CTk()
        try:
            branding.configure_root(root)
            photos=root._image_draw_bot_icons
            self.assertIs(branding.configure_root(root),root)
            self.assertIs(root._image_draw_bot_icons,photos)
            header=ctk.CTkLabel(root,text='',image=branding.header_image())
            header.pack()
            child=ctk.CTkToplevel(root)
            root.after(450,root.quit)
            root.mainloop()
            self.assertTrue(child._image_draw_bot_icon_set)
            for window in (root, child):
                self.assertEqual(Path(applied[window]).resolve(), (ROOT / branding.ICON_ICO).resolve())
                hwnd = user32.GetParent(window.winfo_id())
                self.assertTrue(hwnd)
                for icon_type in (0, 1):  # ICON_SMALL / ICON_BIG, WM_GETICON
                    self.assertTrue(user32.SendMessageW(hwnd, 0x007F, icon_type, 0))
        finally:
            root.destroy()


if __name__ == '__main__': unittest.main()
