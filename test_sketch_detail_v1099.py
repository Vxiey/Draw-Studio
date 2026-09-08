import unittest
import numpy as np
from PIL import Image,ImageDraw
from SketchPlanner import contour_image

class SketchDetailTests(unittest.TestCase):
    def picture(self):
        im=Image.new('RGB',(240,180),'white');d=ImageDraw.Draw(im)
        for x in range(8,230,5):d.line((x,5,x,60),fill=(200,200,200))
        d.ellipse((60,75,180,170),fill='black')
        return im
    def test_simple_suppresses_texture_and_retains_main_contour(self):
        im=self.picture();simple=np.asarray(contour_image(im,detail='Simple').convert('L'))==0
        detailed=np.asarray(contour_image(im,detail='Detailed').convert('L'))==0
        self.assertLess(simple[:65].sum(),detailed[:65].sum())
        self.assertGreater(simple[70:].sum(),100)
    def test_detailed_preserves_previous_default(self):
        im=self.picture();self.assertEqual(contour_image(im).tobytes(),contour_image(im,detail='Detailed').tobytes())
    def test_all_modes_handle_transparency_and_blank(self):
        for mode in ('Simple','Balanced','Detailed'):
            for color in ('white','black',(255,0,0,0)):
                self.assertEqual(contour_image(Image.new('RGBA',(40,40),color),detail=mode).convert('L').getextrema(),(255,255))
    def test_invalid_detail_is_explicit(self):
        with self.assertRaises(ValueError):contour_image(self.picture(),detail='unknown')
