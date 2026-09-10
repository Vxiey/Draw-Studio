import sys
import unittest
from pathlib import Path
from PIL import Image
import tkinter as tk
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

    def test_repeated_destroy_error_is_recognized_without_hiding_other_tcl_errors(self):
        repeated = tk.TclError('can\'t invoke "destroy" command: application has been destroyed')
        self.assertTrue(branding._already_destroyed_tcl_error(repeated))
        self.assertTrue(branding._already_destroyed_tcl_error(tk.TclError('application has been destroyed')))
        self.assertFalse(branding._already_destroyed_tcl_error(tk.TclError('bad window path name ".missing"')))

    def test_destroy_guard_tolerates_minimal_non_tk_test_root(self):
        from unittest.mock import patch
        class FakeRoot:
            pass
        root = FakeRoot()
        with patch.object(branding.sys, 'platform', 'win32'):
            branding._install_destroy_guard(root)
        self.assertFalse(hasattr(root, '_image_draw_bot_destroy_wrapped'))

    def test_destroy_wrapper_is_guarded_and_marks_teardown(self):
        source = (ROOT / 'AppBranding.py').read_text(encoding='utf-8')
        self.assertIn("getattr(root, '_image_draw_bot_destroying', False)", source)
        self.assertIn("getattr(root, 'destroy', None)", source)
        self.assertIn("if not callable(original_destroy)", source)
        self.assertIn("root._image_draw_bot_destroying = True", source)
        self.assertIn("root._image_draw_bot_destroyed = True", source)
        self.assertIn("except tk.TclError as error", source)
        self.assertIn("if not _already_destroyed_tcl_error(error)", source)

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
        from DrawBot import create_root
        from TaskbarIdentity import WindowProperties, window_handle, relaunch_command
        root=create_root()
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
            # Follow StudioUI's dark-mode startup, then hide/show the wrapper.
            ctk.set_appearance_mode('light')
            ctk.set_appearance_mode('dark')
            root.withdraw()
            root.deiconify()
            root.after(650, root.quit)
            root.mainloop()
            with WindowProperties(window_handle(root)) as properties:
                self.assertEqual(properties.get(5), branding.APP_USER_MODEL_ID)
                self.assertEqual(properties.get(3), f'{(ROOT / branding.ICON_ICO).resolve()},0')
                self.assertEqual(properties.get(2), relaunch_command())
                self.assertEqual(properties.get(4), 'Image Draw Bot')
            self.assertTrue(child._image_draw_bot_icon_set)
            for window in (root, child):
                self.assertEqual(Path(applied[window]).resolve(), (ROOT / branding.ICON_ICO).resolve())
                hwnd = user32.GetParent(window.winfo_id())
                self.assertTrue(hwnd)
                for icon_type in (0, 1):  # ICON_SMALL / ICON_BIG, WM_GETICON
                    self.assertTrue(user32.SendMessageW(hwnd, 0x007F, icon_type, 0))
        finally:
            root.destroy()
            # Regression: shutdown paths may converge after Tk has already been
            # destroyed. A repeated branded destroy must be a harmless no-op.
            root.destroy()
        self.assertIsNone(root._image_draw_bot_taskbar_hwnd)


if __name__ == '__main__': unittest.main()