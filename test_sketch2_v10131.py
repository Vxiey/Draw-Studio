import unittest
from PIL import Image,ImageDraw
from Sketch2Planner import contour_image_v2,structure_map

class Sketch2V10131Tests(unittest.TestCase):
    def test_equalish_luminance_color_boundary_survives(self):
        im=Image.new('RGB',(80,40),(235,40,40));ImageDraw.Draw(im).rectangle((40,0,79,39),fill=(30,135,225))
        mask,meta=structure_map(im,detail='Detailed')
        self.assertGreater(int(mask[:,38:42].sum()),5)
        self.assertGreaterEqual(meta['color_boundary_pixels'],1)

    def test_tiny_high_contrast_feature_is_protected(self):
        im=Image.new('RGB',(80,60),'white');d=ImageDraw.Draw(im);d.rectangle((10,10,65,50),outline='black',width=2);d.rectangle((35,28,37,30),fill='black')
        out,meta=contour_image_v2(im,detail='Detailed')
        gray=out.convert('L')
        local=[gray.getpixel((x,y)) for y in range(25,34) for x in range(32,41)]
        self.assertIn(0,local)
        self.assertGreater(meta['ink_pixels'],20)

    def test_deterministic(self):
        im=Image.new('RGB',(64,48),'white');ImageDraw.Draw(im).ellipse((8,8,56,40),fill=(40,100,210))
        a,ma=contour_image_v2(im,detail='Balanced');b,mb=contour_image_v2(im,detail='Balanced')
        self.assertEqual(a.tobytes(),b.tobytes());self.assertEqual(ma,mb)

if __name__=='__main__':unittest.main()
