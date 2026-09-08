import unittest
from PIL import Image, ImageDraw

from AdaptiveColorCount import recommend_adaptive_color_count
from DynamicColors import resolve_exact_color_limit


class Step5AdaptiveColorCountV10129Tests(unittest.TestCase):
    def test_simple_flat_logo_uses_less_than_quality_ceiling(self):
        im=Image.new('RGB',(160,100),'white');d=ImageDraw.Draw(im)
        d.rectangle((15,20,145,80),fill=(245,205,25))
        count,meta=recommend_adaptive_color_count(im,ceiling=16,fidelity='Faithful')
        self.assertGreaterEqual(count,2)
        self.assertLessEqual(count,3)
        self.assertLessEqual(meta['significant_color_buckets'],5)
        self.assertFalse(meta['time_budget_applied'])

    def test_complex_gradient_uses_more_colours_than_flat_logo(self):
        simple=Image.new('RGB',(160,100),(245,205,25))
        complex_im=Image.new('RGB',(160,100))
        p=complex_im.load()
        for y in range(complex_im.height):
            for x in range(complex_im.width):
                p[x,y]=(int(x/159*255),int(y/99*255),int(((x+y)/(159+99))*255))
        simple_count,_=recommend_adaptive_color_count(simple,ceiling=24,fidelity='Faithful')
        complex_count,meta=recommend_adaptive_color_count(complex_im,ceiling=24,fidelity='Faithful')
        self.assertGreater(complex_count,simple_count)
        self.assertGreaterEqual(complex_count,12)
        self.assertGreater(meta['complexity_score'],0.45)

    def test_four_large_hue_families_fit_structural_floor(self):
        im=Image.new('RGB',(120,120),'white');d=ImageDraw.Draw(im)
        d.rectangle((0,0,59,59),fill=(235,35,25))
        d.rectangle((60,0,119,59),fill=(245,220,25))
        d.rectangle((0,60,59,119),fill=(35,190,55))
        d.rectangle((60,60,119,119),fill=(30,70,230))
        count,meta=recommend_adaptive_color_count(im,ceiling=16,fidelity='Faithful')
        self.assertGreaterEqual(count,4)
        self.assertTrue({'red','yellow','green','blue'}.issubset(set(meta['dominant_hue_families'])))

    def test_recommendation_is_deterministic(self):
        im=Image.new('RGB',(91,67));p=im.load()
        for y in range(im.height):
            for x in range(im.width):p[x,y]=((x*7)%256,(y*11)%256,((x+y)*5)%256)
        a,ma=recommend_adaptive_color_count(im,ceiling=20,fidelity='Balanced')
        b,mb=recommend_adaptive_color_count(im,ceiling=20,fidelity='Balanced')
        self.assertEqual(a,b)
        self.assertEqual(ma,mb)

    def test_legacy_resolver_still_respects_explicit_and_old_auto_default(self):
        self.assertEqual(resolve_exact_color_limit('8',draw_quality='Pixel Accurate'),8)
        self.assertEqual(resolve_exact_color_limit('Auto',draw_quality='High likeness'),16)

    def test_preview_flag_does_not_change_image_recommendation(self):
        im=Image.new('RGB',(120,80))
        p=im.load()
        for y in range(im.height):
            for x in range(im.width):p[x,y]=(x*2%256,y*3%256,(x+y)%256)
        a,_=recommend_adaptive_color_count(im,ceiling=20,fidelity='Faithful',preview=False)
        b,_=recommend_adaptive_color_count(im,ceiling=20,fidelity='Faithful',preview=True)
        self.assertEqual(a,b)

    def test_release_build_includes_adaptive_color_count_module(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'AdaptiveColorCount'",source)


if __name__=='__main__':
    unittest.main()
