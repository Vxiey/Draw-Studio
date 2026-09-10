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
            self.assertEqual(Path(root.tk.call('wm', 'iconbitmap', root._w)).name,'image-draw-bot-icon.ico')
            self.assertEqual(Path(child.tk.call('wm', 'iconbitmap', child._w)).name,'image-draw-bot-icon.ico')
        finally:
            root.destroy()


if __name__ == '__main__': unittest.main()
