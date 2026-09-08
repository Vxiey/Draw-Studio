import unittest
from PIL import Image, ImageDraw

from DynamicColors import build_dynamic_color_strokes, resolve_exact_color_limit
from GameProfiles import profile_defaults

class ColorEngineV3Tests(unittest.TestCase):
    def test_auto_limit(self):
        self.assertEqual(resolve_exact_color_limit('Auto', draw_quality='Balanced', preview=False), 12)
        self.assertEqual(resolve_exact_color_limit('Auto', draw_quality='High likeness', preview=False), 16)
        self.assertEqual(resolve_exact_color_limit('Auto', draw_quality='Maximum likeness', preview=False), 20)
        self.assertEqual(resolve_exact_color_limit('Auto', draw_quality='GPU enhanced', preview=False), 24)
        self.assertEqual(resolve_exact_color_limit('Auto', draw_quality='High likeness', preview=True), 8)

    def test_reduces_many_similar_colors(self):
        im=Image.new('RGB',(40,1))
        shades=[(40+i,80+i//2,160+i//3) for i in range(40)]
        im.putdata(shades)
        palette=((0,0,0),(255,255,255),(50,90,170))
        groups,colors,selectors,meta=build_dynamic_color_strokes(im,palette,max_colors=20,skip_white=False,exact_available=True)
        self.assertLessEqual(meta['reduced_colors'],20)
        self.assertLessEqual(meta['active_colors'],20)
        self.assertEqual(len(colors), len(selectors))

    def test_balances_exact_and_palette(self):
        im=Image.new('RGB',(20,2))
        d=ImageDraw.Draw(im)
        d.rectangle((0,0,9,1), fill=(120,90,200))   # far from palette
        d.rectangle((10,0,19,1), fill=(250,10,5))   # close to red
        palette=((255,0,0),(0,255,0),(0,0,255))
        groups,colors,selectors,meta=build_dynamic_color_strokes(im,palette,max_colors=2,skip_white=False,exact_available=True)
        kinds=sorted(s['kind'] for s in selectors if s)
        self.assertEqual(meta['custom_exact_colors'],1)
        self.assertEqual(meta['palette_fallback_colors'],1)
        self.assertEqual(kinds,['custom','palette'])

    def test_custom_dialog_budget_prioritises_coverage(self):
        im=Image.new('RGB',(20,20),'white')
        d=ImageDraw.Draw(im)
        d.rectangle((0,0,15,15), fill=(110,90,200))     # large, poor palette match
        d.rectangle((16,0,19,7), fill=(170,120,30))     # medium
        d.rectangle((16,8,19,11), fill=(20,170,170))    # small
        d.rectangle((16,12,19,15), fill=(220,50,120))   # small
        palette=((255,0,0),(0,255,0),(0,0,255),(255,255,255))
        groups,colors,selectors,meta=build_dynamic_color_strokes(im,palette,max_colors=4,skip_white=True,exact_available=True)
        custom=[s for s in selectors if s['kind']=='custom']
        self.assertLess(len(custom), 4)  # custom dialogs are bounded
        self.assertGreaterEqual(len(custom), 1)
        # The largest colour should be among the chosen exact colours because
        # groups/selectors are ordered by coverage descending.
        self.assertEqual(selectors[0]['kind'], 'custom')

    def test_profile_default_uses_adaptive_exact(self):
        self.assertEqual(profile_defaults('Microsoft Paint')['custom_color_workflow'], 'Adaptive exact (recommended)')

if __name__=='__main__':
    unittest.main()
