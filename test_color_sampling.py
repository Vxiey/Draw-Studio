import unittest
from PIL import Image, ImageDraw
from Colors import argb_to_rgb, normalize_rgb, validate_calibration
from PaletteMaps import detect_color_swatches


class ColorConversionTests(unittest.TestCase):
    def test_argb_hex_and_tuple_are_composited_to_rgb(self):
        self.assertEqual(argb_to_rgb('#80FF0000'), (255, 127, 127))
        self.assertEqual(argb_to_rgb((255, 12, 34, 56)), (12, 34, 56))
        self.assertEqual(argb_to_rgb((0, 12, 34, 56)), (255, 255, 255))

    def test_normalize_accepts_rgb_and_argb(self):
        self.assertEqual(normalize_rgb('#112233'), (17, 34, 51))
        self.assertEqual(normalize_rgb('FF112233'), (17, 34, 51))
        self.assertEqual(normalize_rgb(0xFF112233), (17, 34, 51))
        self.assertEqual(normalize_rgb((128, 0, 0, 255)), (127, 127, 255))
        self.assertEqual(normalize_rgb('(128, 255, 0, 0)'), (255, 127, 127))

    def test_calibration_accepts_argb_and_normalizes_it(self):
        rows=validate_calibration({'version':3,'colors':[
            {'name':'Transparent red','position':[10,20],'argb':[128,255,0,0]}
        ]})
        self.assertEqual(rows[0]['rgb'], [255,127,127])
        self.assertNotIn('argb', rows[0])


class AreaColorDetectionTests(unittest.TestCase):
    def test_detects_only_solid_swatches_inside_selected_area(self):
        image=Image.new('RGB',(130,55),(230,230,230))
        draw=ImageDraw.Draw(image)
        colors=[(255,0,0),(0,180,0),(0,80,230),(255,255,255)]
        boxes=[(8,8,30,30),(38,8,60,30),(68,8,90,30),(98,8,120,30)]
        for box,color in zip(boxes,colors):
            draw.rectangle(box,fill=(20,20,20))
            inner=(box[0]+3,box[1]+3,box[2]-3,box[3]-3)
            draw.rectangle(inner,fill=color)
        positions,found,stats=detect_color_swatches(image,(100,200))
        self.assertEqual(found,colors)
        self.assertEqual(stats['found'],4)
        for x,y in positions:
            self.assertGreaterEqual(x,100);self.assertGreaterEqual(y,200)

    def test_outer_background_is_not_returned_as_a_color(self):
        image=Image.new('RGB',(120,50),(210,210,210))
        draw=ImageDraw.Draw(image)
        draw.rectangle((45,12,74,41),fill=(15,15,15))
        draw.rectangle((49,16,70,37),fill=(255,80,20))
        positions,found,stats=detect_color_swatches(image)
        self.assertEqual(found,[(255,80,20)])
        self.assertEqual(stats['found'],1)

    def test_round_paint_swatches_are_supported(self):
        image=Image.new('RGB',(100,40),(235,235,235))
        draw=ImageDraw.Draw(image)
        colors=[(255,0,0),(0,200,40),(0,80,255)]
        for i,color in enumerate(colors):
            x=8+i*30
            draw.ellipse((x,7,x+20,27),fill=color)
        _,found,_=detect_color_swatches(image)
        self.assertEqual(found,colors)

    def test_noise_without_solid_swatch_is_rejected(self):
        image=Image.new('RGB',(30,30))
        px=image.load()
        for y in range(30):
            for x in range(30):px[x,y]=((x*17+y*13)%256,(x*7+y*19)%256,(x*23+y*3)%256)
        with self.assertRaises(ValueError):detect_color_swatches(image)


if __name__=='__main__':
    unittest.main()
