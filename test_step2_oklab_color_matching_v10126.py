import unittest

from AdvancedColor import _closest_palette_index_cached
from ColorFidelity import delta_e_oklab, mapping_pair_metrics, palette_match_cost, rgb_to_oklab
from ExactColorEngine import score_candidate
from PixelAccuratePlanner import exact_palette_map
from PIL import Image


class Step2OKLabColorMatchingV10126Tests(unittest.TestCase):
    def test_oklab_identity_is_zero(self):
        rgb=(242,200,35)
        self.assertEqual(delta_e_oklab(rgb,rgb),0.0)
        L,a,b=rgb_to_oklab(rgb)
        self.assertGreater(L,0.0)
        self.assertTrue(all(isinstance(v,float) for v in (L,a,b)))

    def test_yellow_prefers_yellow_over_light_pink(self):
        source=(242,200,35)
        palette=((254,175,168),(255,193,38),(255,120,41))
        names=('Light Pink','Yellow','Orange')
        index=_closest_palette_index_cached(source,palette,names,'Perceptual match','Calibrated palette','Faithful')
        self.assertEqual(index,1)

    def test_yellow_without_yellow_prefers_related_orange_over_pink(self):
        source=(242,200,35)
        orange=(255,150,35)
        pink=(247,155,165)
        self.assertLess(
            palette_match_cost(source,orange,color_rendering='Perceptual match',fidelity='Faithful'),
            palette_match_cost(source,pink,color_rendering='Perceptual match',fidelity='Faithful'))

    def test_exact_candidate_score_uses_oklab_and_rejects_pink_family_swap(self):
        source=(242,200,35)
        yellow=score_candidate(source,(255,193,38),fidelity='Faithful')
        pink=score_candidate(source,(254,175,168),fidelity='Faithful')
        self.assertGreater(yellow.oklab_distance,0.0)
        self.assertLess(yellow.total_cost,pink.total_cost)
        self.assertGreater(pink.hue_error,45.0)

    def test_mapping_diagnostics_include_oklab_distance(self):
        metrics=mapping_pair_metrics((242,200,35),(254,175,168))
        self.assertIn('delta_e_oklab',metrics)
        self.assertGreater(metrics['delta_e_oklab'],10.0)
        self.assertGreater(metrics['hue_error'],45.0)


    def test_pixel_accurate_path_uses_oklab_and_faithful_hue_protection(self):
        source=Image.new('RGB',(12,6),(242,200,35))
        palette=((254,175,168),(255,193,38),(255,120,41))
        index_map,drawable,_rgb,meta=exact_palette_map(
            source,palette,color_rendering='Perceptual match',color_fidelity='Faithful',
            skip_white=False,gpu_mode='CPU')
        self.assertTrue(drawable.all())
        self.assertEqual(set(index_map.reshape(-1).tolist()),{1})
        self.assertEqual(meta['palette_distance'],'OKLab')
        self.assertEqual(meta['palette_fidelity'],'Faithful')

    def test_rgb_nearest_mode_remains_independent_of_oklab_fidelity_terms(self):
        source=(100,120,140);candidate=(105,118,136)
        fast=palette_match_cost(source,candidate,color_rendering='RGB nearest',fidelity='Fast')
        exact=palette_match_cost(source,candidate,color_rendering='RGB nearest',fidelity='Exact')
        self.assertAlmostEqual(fast,exact,places=9)


if __name__=='__main__':
    unittest.main()
