import tempfile
import unittest
from pathlib import Path
from PIL import Image
from DrawBot import load_image
from ImageFormatInfo import image_label

class ImageFormatTests(unittest.TestCase):
    def test_content_wins_over_extension(self):
        with tempfile.TemporaryDirectory() as d:
            for fmt, suffix in [('PNG','.jpg'),('JPEG','.png'),('BMP','.dat'),('WEBP','.jpg')]:
                p=Path(d)/('image'+suffix)
                Image.new('RGB',(5,7),'red').save(p,format=fmt)
                image=load_image(p)
                self.assertEqual(image.info['draw_studio_format'],fmt)
                self.assertIn(fmt,image_label(image,'test'))

    def test_opaque_png_is_not_transparent(self):
        image=Image.new('RGBA',(3,3),'red');image.info['draw_studio_format']='PNG'
        self.assertIn('no transparency',image_label(image,'test'))

    def test_actual_transparency(self):
        image=Image.new('RGBA',(3,3),(255,0,0,100))
        self.assertIn('transparent pixels',image_label(image,'test'))

    def test_clipboard_does_not_invent_original_file_type(self):
        self.assertIn('decoded pixels',image_label(Image.new('RGB',(2,2)),'paste'))

    def test_fake_image_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.png';p.write_text('not an image')
            with self.assertRaisesRegex(ValueError,'Could not read'):load_image(p)
