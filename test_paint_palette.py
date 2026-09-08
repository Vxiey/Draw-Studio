import unittest
from PIL import Image,ImageDraw
from PaletteMaps import sample_paint_grid

class PaintPaletteTests(unittest.TestCase):
    def palette(self,colors,round=True,background=(240,240,240)):
        im=Image.new('RGB',(len(colors)*24,24),background);d=ImageDraw.Draw(im)
        for i,c in enumerate(colors):
            if c is not None:
                box=(i*24+3,3,i*24+21,21)
                (d.ellipse if round else d.rectangle)(box,fill=c)
        return im
    def test_duplicate_colors_merge_without_losing_distinct_shades(self):
        im=self.palette([(255,0,0),(255,0,0),(251,0,0),None])
        pos,colors,stats=sample_paint_grid(im,1,4,(-100,20))
        self.assertEqual(colors,[(255,0,0),(251,0,0)])
        self.assertEqual(stats,{'duplicates':1,'skipped':1})
        self.assertEqual(pos,[(-88,32),(-40,32)])
    def test_center_pixel_noise_uses_real_nearby_color(self):
        im=self.palette([(10,100,200)]);im.putpixel((12,12),(255,255,255))
        pos,colors,stats=sample_paint_grid(im,1,1)
        self.assertEqual(colors,[(10,100,200)])
        self.assertEqual(im.getpixel(pos[0]),colors[0])
    def test_blank_palette_rejected(self):
        with self.assertRaisesRegex(ValueError,'No clear Paint colors'):sample_paint_grid(self.palette([None,None]),1,2)
    def test_square_swatches_and_white_black(self):
        _,colors,_=sample_paint_grid(self.palette([(255,255,255),(0,0,0)],round=False),1,2)
        self.assertEqual(colors,[(255,255,255),(0,0,0)])
    def test_dark_background_and_gray_swatches(self):
        _,colors,_=sample_paint_grid(self.palette([(90,90,90),(140,140,140)],background=(30,30,30)),1,2)
        self.assertEqual(colors,[(90,90,90),(140,140,140)])
    def test_busy_center_skipped(self):
        im=self.palette([(10,100,200),(255,0,0)])
        ImageDraw.Draw(im).rectangle((10,10,12,12),fill=(0,0,0))
        _,colors,stats=sample_paint_grid(im,1,2)
        self.assertEqual(colors,[(255,0,0)]);self.assertEqual(stats['skipped'],1)

if __name__=='__main__':unittest.main()
