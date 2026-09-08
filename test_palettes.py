import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from PaletteMaps import SKRIBBL, detect_preset, sample_grid
from Colors import save_calibration


def palette_image(scale=20):
    im=Image.new('RGB',(13*(scale+4)+4,2*(scale+4)+4),(231,233,235))
    d=ImageDraw.Draw(im);centers=[]
    for i,rgb in enumerate(SKRIBBL.colors):
        x=4+(i//2)*(scale+4);y=4+(i%2)*(scale+4)
        d.rectangle((x,y,x+scale-1,y+scale-1),fill=rgb)
        centers.append((x+(scale-1)//2,y+(scale-1)//2))
    return im,centers


class PaletteTests(unittest.TestCase):
    def test_native_indices_and_negative_monitor_offset(self):
        im,points=palette_image()
        self.assertEqual(detect_preset(im,SKRIBBL,(-100,50)),[(x-100,y+50) for x,y in points])
        self.assertEqual(SKRIBBL.colors[4],(239,19,11))
        self.assertEqual(len(SKRIBBL.colors),26)

    def test_zoom(self):
        im,points=palette_image(32)
        self.assertEqual(detect_preset(im,SKRIBBL),points)

    def test_missing_swatch_rejected(self):
        im,_=palette_image();ImageDraw.Draw(im).rectangle((4,4,23,23),fill=(1,2,3))
        with self.assertRaisesRegex(ValueError,'White'):detect_preset(im,SKRIBBL)

    def test_duplicate_swatch_rejected(self):
        im,_=palette_image();big=Image.new('RGB',(im.width,im.height+30),(231,233,235));big.paste(im)
        ImageDraw.Draw(big).rectangle((4,im.height+4,23,im.height+23),fill=SKRIBBL.colors[4])
        with self.assertRaisesRegex(ValueError,'Red'):detect_preset(big,SKRIBBL)

    def test_grid_actual_rgb_and_order(self):
        im=Image.new('RGB',(40,20));d=ImageDraw.Draw(im)
        colors=[(1,2,3),(10,20,30),(100,110,120),(200,210,220)]
        for i,c in enumerate(colors):d.rectangle((i%2*20,i//2*10,i%2*20+19,i//2*10+9),fill=c)
        positions,actual=sample_grid(im,2,2,(-40,0))
        self.assertEqual(actual,colors);self.assertEqual(positions,[(-30,5),(-10,5),(-30,15),(-10,15)])

    def test_grid_bad_marking_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate colors'):sample_grid(Image.new('RGB',(40,20),'white'),2,2)
        im=Image.new('RGB',(20,20),'white');im.putpixel((10,10),(0,0,0))
        with self.assertRaisesRegex(ValueError,'solid'):sample_grid(im,1,1)

    def test_atomic_map_export_keeps_native_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'map.json'
            save_calibration([(i*10,10) for i in range(26)],SKRIBBL.colors,path,names=SKRIBBL.names,indices=list(range(26)))
            rows=json.loads(path.read_text())['colors']
            self.assertEqual(rows[4],{'name':'Red','rgb':[239,19,11],'position':[40,10],'game_index':4})

if __name__=='__main__':unittest.main()
