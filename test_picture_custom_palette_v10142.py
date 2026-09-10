import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, ImageDraw

import PictureCustomPalette as pcp


class Var:
    def __init__(self, value): self.value=value
    def get(self): return self.value
    def set(self, value): self.value=value


class Mouse:
    def __init__(self): self.actions=[]; self.armed=False
    def arm_input(self): self.armed=True; self.actions.append(('arm',))
    def disarm_input(self): self.armed=False; self.actions.append(('disarm',))
    def move(self, x, y): self.actions.append(('move', int(x), int(y)))
    def click(self): self.actions.append(('click',))


class Keyboard:
    def __init__(self): self.actions=[]
    def press_and_release(self, key): self.actions.append(('press', str(key)))
    def write(self, text, delay=0): self.actions.append(('write', str(text)))


class Status:
    def __init__(self): self.value=''
    def set(self, value): self.value=str(value)


def picture():
    im=Image.new('RGB',(96,72),(245,245,245));d=ImageDraw.Draw(im)
    d.rectangle((4,5,44,65),fill=(201,43,37))
    d.ellipse((48,8,88,56),fill=(31,118,221))
    d.rectangle((57,20,61,24),fill=(7,8,9))
    d.line((10,10,80,60),fill=(45,180,85),width=2)
    return im


class PictureCustomPaletteTests(unittest.TestCase):
    def test_image_fingerprint_is_stable_and_pixel_sensitive(self):
        a=picture();b=a.copy()
        self.assertEqual(pcp.image_fingerprint(a),pcp.image_fingerprint(b))
        b.putpixel((0,0),(1,2,3))
        self.assertNotEqual(pcp.image_fingerprint(a),pcp.image_fingerprint(b))

    def test_cache_is_isolated_by_image_and_calibration(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(pcp,'data_dir',return_value=Path(tmp)):
            pal=pcp.PicturePalette('a'*64,'cal-A',(20,10),8,'Faithful',((1,2,3),),((1,2,3),),(),(.5,),False)
            pcp.save_palette(pal)
            hit=pcp.load_cached_palette('a'*64,'cal-A',max_colors=8,fidelity='Faithful')
            self.assertIsNotNone(hit);self.assertTrue(hit.cache_hit)
            self.assertIsNone(pcp.load_cached_palette('a'*64,'cal-B',max_colors=8,fidelity='Faithful'))
            self.assertIsNone(pcp.load_cached_palette('b'*64,'cal-A',max_colors=8,fidelity='Faithful'))

    def test_rgb_sequence_types_exact_channels_and_disarms(self):
        mouse=Mouse();keyboard=Keyboard();waits=[]
        controls={'OpenCustomColor':(10,10),'RedField':(20,20),'GreenField':(30,30),'BlueField':(40,40),'ConfirmColor':(50,50)}
        count=pcp.apply_custom_rgb_sequence(mouse,keyboard,controls,[(12,34,56),(201,4,9)],wait=lambda s:waits.append(s))
        self.assertEqual(count,2);self.assertFalse(mouse.armed)
        self.assertEqual(mouse.actions[0],('arm',));self.assertEqual(mouse.actions[-1],('disarm',))
        self.assertEqual([a for a in keyboard.actions if a[0]=='write'],[('write','12'),('write','34'),('write','56'),('write','201'),('write','4'),('write','9')])
        self.assertEqual(keyboard.actions.count(('press','ctrl+a')),6)

    def test_rgb_sequence_cancel_always_disarms_and_escapes_open_dialog(self):
        mouse=Mouse();keyboard=Keyboard();controls={'OpenCustomColor':(10,10),'RedField':(20,20),'GreenField':(30,30),'BlueField':(40,40),'ConfirmColor':(50,50)}
        calls={'n':0}
        def cancelled():
            calls['n']+=1
            return calls['n']>=3
        with self.assertRaises(InterruptedError):
            pcp.apply_custom_rgb_sequence(mouse,keyboard,controls,[(12,34,56)],cancelled=cancelled,wait=lambda _s:None)
        self.assertFalse(mouse.armed);self.assertEqual(mouse.actions[-1],('disarm',))
        self.assertIn(('press','esc'),keyboard.actions)

    def test_dialog_not_ready_prevents_all_numeric_input(self):
        mouse=Mouse();keyboard=Keyboard()
        controls={'OpenCustomColor':(10,10),'RedField':(20,20),'GreenField':(30,30),'BlueField':(40,40),'ConfirmColor':(50,50)}
        def not_ready(): raise TimeoutError('Paint not ready')
        with self.assertRaises(TimeoutError):
            pcp.apply_custom_rgb_sequence(mouse,keyboard,controls,[(12,34,56)],
                wait=lambda _:None,dialog_ready=not_ready)
        self.assertFalse(any(a[0]=='write' or a==('press','ctrl+a') for a in keyboard.actions))
        self.assertFalse(mouse.armed)

    def test_unclosed_dialog_prevents_next_color_and_completion(self):
        mouse=Mouse();keyboard=Keyboard();progress=[]
        controls={'OpenCustomColor':(10,10),'RedField':(20,20),'GreenField':(30,30),'BlueField':(40,40),'ConfirmColor':(50,50)}
        def still_open(): raise TimeoutError('Paint dialog still open')
        with self.assertRaises(TimeoutError):
            pcp.apply_custom_rgb_sequence(mouse,keyboard,controls,[(12,34,56),(7,8,9)],
                wait=lambda _:None,dialog_ready=lambda:{'RedField':(22,22)},
                dialog_closed=still_open,progress=lambda *a:progress.append(a))
        self.assertEqual([a for a in keyboard.actions if a[0]=='write'],[('write','12'),('write','34'),('write','56')])
        self.assertIn(('move',22,22),mouse.actions)
        self.assertNotIn(('move',20,20),mouse.actions)
        self.assertEqual(progress,[])
        self.assertFalse(mouse.armed)

    def test_picture_palette_is_bounded_and_uses_production_dynamic_colors(self):
        fallback=((0,0,0),(255,255,255),(255,0,0),(0,0,255),(0,128,0),(128,128,128))
        with tempfile.TemporaryDirectory() as tmp, patch.object(pcp,'data_dir',return_value=Path(tmp)):
            pal=pcp.build_picture_palette(picture(),fallback,max_colors=8,fidelity='Faithful',calibration_fingerprint='cal')
            self.assertLessEqual(len(pal.colors),8)
            self.assertLessEqual(len(pal.custom_colors),8)
            self.assertEqual(pal.source_size,(96,72))
            self.assertTrue(pal.colors)
            cached=pcp.build_picture_palette(picture(),fallback,max_colors=8,fidelity='Faithful',calibration_fingerprint='cal')
            self.assertTrue(cached.cache_hit)
            self.assertEqual(cached.colors,pal.colors)

    def test_ui_entry_guards_image_and_profile_without_worker(self):
        for profile,image,needle in [('Gartic Phone',picture(),'Microsoft Paint'),('Microsoft Paint',None,'Load an image')]:
            app=SimpleNamespace(activity=None,closing=False,game=Var(profile),original=image,status=Status())
            app.begin_worker=lambda *_a,**_k:self.fail('worker must not start')
            self.assertFalse(pcp.start_picture_custom_palette(app))
            self.assertIn(needle,app.status.value)

    def test_picture_palette_skips_edit_colors_for_single_color_or_black_sketch(self):
        for single,outline,needle in ((True,False,'Single-color'),(False,True,'Black contour')):
            app=SimpleNamespace(activity=None,closing=False,game=Var('Microsoft Paint'),original=picture(),
                                paint_simple=Var(single),outline=Var(outline),paint_tool=Var('Pencil'),status=Status())
            app.begin_worker=lambda *_a,**_k:self.fail('worker must not start')
            self.assertFalse(pcp.start_picture_custom_palette(app))
            self.assertIn(needle,app.status.value)
            self.assertIn('will not be opened',app.status.value)

    def test_studio_ui_exposes_picture_palette_only_in_paint_scope(self):
        source=Path('StudioUI.py').read_text(encoding='utf-8')
        self.assertIn('Custom color palette for picture',source)
        self.assertIn("(a.picture_palette_button,'paint')",source)


if __name__=='__main__':unittest.main()
