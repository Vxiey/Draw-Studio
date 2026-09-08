import unittest
from PIL import Image, ImageDraw
import DrawBot
from SketchPlanner import black_index, contour_image

class BlackSketchTests(unittest.TestCase):
    def picture(self):
        im=Image.new('RGB',(120,100),'white')
        d=ImageDraw.Draw(im)
        d.rectangle((15,15,55,80),fill='red')
        d.ellipse((65,20,105,80),fill='blue')
        return im

    def options(self,**changes):
        o=dict(detail=8,delay=.01,lines=True,skip_white=False,contrast=1,
               outline=True,brush_px=1,max_seconds=180,subject_focus='Off',
               background_fill='Conservative',background_simplification='Strong simplify',
               render_style='Portrait / shaded',color_layers='Auto',gpu_mode='CPU')
        o.update(changes)
        return o

    def test_contours_only_no_interior_fills(self):
        im=self.picture();before=im.tobytes();out=contour_image(im)
        self.assertEqual(im.tobytes(),before)
        self.assertEqual(set(out.convert('L').getdata()),{0,255})
        self.assertEqual(out.getpixel((30,40)),(255,255,255,255))
        self.assertEqual(out.getpixel((85,50)),(255,255,255,255))
        self.assertLess(sum(v==0 for v in out.convert('L').getdata()),1000)

    def test_uniform_and_transparent_images_have_no_ink(self):
        for color in ('black','white',(200,20,30,0)):
            out=contour_image(Image.new('RGBA',(40,30),color))
            self.assertEqual(out.convert('L').getextrema(),(255,255))

    def test_tiny_images(self):
        for size in ((1,1),(1,10),(10,1)):
            self.assertEqual(contour_image(Image.new('RGB',size)).size,size)

    def test_cancellation(self):
        with self.assertRaises(InterruptedError):contour_image(self.picture(),lambda:True)

    def test_black_palette_required(self):
        self.assertEqual(black_index([(255,0,0),(0,0,0)]),1)
        with self.assertRaises(ValueError):black_index([(255,0,0),(0,0,20)])

    def test_plan_black_only_despite_color_settings(self):
        for mode in ('Auto','Gartic Phone','Skribbl.io'):
            p=DrawBot.make_plan(self.picture(),(120,100),self.options(profile_engine=mode))
            active=[DrawBot.allColors[i].RGB for i,g in enumerate(p['groups']) if g]
            self.assertEqual(active,[(0,0,0)])
            self.assertTrue(p['options']['black_sketch'])
            self.assertEqual(p['options']['fill_regions'],[])
            self.assertNotIn('portrait_stats',p['options'])
            self.assertEqual(set(p['preview'].getdata()),{(0,0,0),(255,255,255)})

    def test_single_color_paint_skips_shading(self):
        p=DrawBot.make_plan(self.picture(),(120,100),self.options(paint_current_color=True))
        self.assertEqual(len(p['groups']),1)
        self.assertGreater(p['count'],0)
        self.assertNotIn('portrait_stats',p['options'])

    def test_test_draw_uses_only_black(self):
        p=DrawBot.make_test_plan((120,100),self.options())
        self.assertEqual([DrawBot.allColors[i].RGB for i,g in enumerate(p['groups']) if g],[(0,0,0)])

if __name__=='__main__':unittest.main()
