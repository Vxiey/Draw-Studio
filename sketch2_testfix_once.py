from pathlib import Path
p=Path('test_sketch2_v10131.py')
text=p.read_text(encoding='utf-8')
old="""        out,meta=contour_image_v2(im,detail='Detailed')
        self.assertLess(out.convert('L').getpixel((36,29)),255)
        self.assertGreater(meta['ink_pixels'],20)
"""
new="""        out,meta=contour_image_v2(im,detail='Detailed')
        gray=out.convert('L')
        local=[gray.getpixel((x,y)) for y in range(25,34) for x in range(32,41)]
        self.assertIn(0,local)
        self.assertGreater(meta['ink_pixels'],20)
"""
if text.count(old)!=1:raise SystemExit('Sketch2 tiny-feature test anchor missing')
p.write_text(text.replace(old,new,1),encoding='utf-8')
print('SKETCH2_TEST_FIX=APPLIED')
