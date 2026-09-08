import unittest
from PIL import Image

from ColorFidelity import palette_match_cost, mapping_pair_metrics, validate_color_fidelity
from GameProfiles import profile_defaults
from ProfileEngine import resolve_profile_policy
from PreviewLayers import build_auxiliary_previews
from ProfileIsolation import SETTING_NAMES
from GarticPhoneFastRenderer import optimize_gartic_phone_groups


class ColorFidelity120Tests(unittest.TestCase):
    def test_faithful_penalizes_dark_bias_more_than_fast(self):
        src=(224,174,128)
        dark=(160,112,82)
        similar=(230,158,122)
        fast_gap=(palette_match_cost(src,dark,color_rendering='Perceptual match',fidelity='Fast')-
                  palette_match_cost(src,similar,color_rendering='Perceptual match',fidelity='Fast'))
        faithful_gap=(palette_match_cost(src,dark,color_rendering='Perceptual match',fidelity='Faithful')-
                      palette_match_cost(src,similar,color_rendering='Perceptual match',fidelity='Faithful'))
        self.assertGreater(faithful_gap,fast_gap)

    def test_preview_fill_layer_no_longer_forces_068_brightness(self):
        src=Image.new('RGB',(12,8),(180,140,100))
        result=build_auxiliary_previews(src,(12,8),[[]],[(0,0,0)],lambda x,y:(x,y),1,{})
        self.assertEqual(result['fill'].getpixel((6,4)),(180,140,100))
        self.assertEqual(result['color'].getpixel((6,4)),(180,140,100))

    def test_gartic_default_is_faithful_perceptual(self):
        defaults=profile_defaults('Gartic Phone')
        self.assertEqual(defaults['color_rendering'],'Perceptual match')
        self.assertEqual(defaults['color_fidelity'],'Faithful')

    def test_gartic_auto_policy_keeps_faithful_color(self):
        requested={
            'mode':'Smart paths (recommended)','shape_model':'Better shapes v2','shape_order':'Fill first',
            'progressive_rendering':'Off','quality':'Balanced','speed':'Fast','precision':'Normal',
            'draw_quality':'Balanced','planning_resolution':'Standard','background_fill':'Off',
            'background_simplification':'Strong','color_grouping':'Reduced palette','color_workflow':'Finish color first',
            'stroke_optimizer':'Smart merge','adaptive_detail':'Strong simplify','visual_verification':'Off',
            'color_rendering':'RGB nearest','color_fidelity':'Fast','color_layers':'Off',
            'custom_color_workflow':'Calibrated palette','exact_color_limit':'8','time_budget_mode':'60 sec',
            'target_stroke_count':'Auto','max_stroke_cap':'1000','planning_watchdog':'On','resource_scheduler':'Auto',
            'render_style':'Auto','fill_engine':'Auto','use_region_fill_engine':True,'fill_aggressiveness':'Balanced',
            'tool_strategy':'Auto','edge_behavior':'Hard Clip','target_stroke_custom':'700',
        }
        effective,_=resolve_profile_policy('Gartic Phone',requested,mode='Auto')
        self.assertEqual(effective['color_rendering'],'Perceptual match')
        self.assertEqual(effective['color_fidelity'],'Faithful')

    def test_pixel_accurate_policy_uses_exact_fidelity(self):
        requested={
            'draw_quality':'Pixel Accurate','quality':'Balanced','planning_resolution':'Standard',
            'background_simplification':'Strong','color_grouping':'Reduced palette','stroke_optimizer':'Smart merge',
            'adaptive_detail':'Strong simplify','time_budget_mode':'60 sec','target_stroke_count':'Auto',
            'max_stroke_cap':'1000','progressive_rendering':'Off','color_rendering':'RGB nearest',
            'color_fidelity':'Faithful','mode':'Smart paths (recommended)','shape_model':'Better shapes v2','shape_order':'Fill first',
            'speed':'Fast','precision':'Normal','background_fill':'Off','color_workflow':'Finish color first',
            'visual_verification':'Off','color_layers':'Off','custom_color_workflow':'Calibrated palette','exact_color_limit':'8',
            'planning_watchdog':'On','resource_scheduler':'Auto','render_style':'Auto','fill_engine':'Auto',
            'use_region_fill_engine':True,'fill_aggressiveness':'Balanced','tool_strategy':'Auto','edge_behavior':'Hard Clip',
            'target_stroke_custom':'700',
        }
        effective,_=resolve_profile_policy('Gartic Phone',requested,mode='Auto')
        self.assertEqual(effective['color_fidelity'],'Exact')

    def test_pair_metrics_detect_lighter_and_darker(self):
        dark=mapping_pair_metrics((220,180,140),(120,90,70))
        self.assertLess(dark['mapped_lightness'],dark['source_lightness'])
        self.assertGreater(dark['delta_e76'],0)

    def test_profile_isolation_tracks_color_fidelity(self):
        self.assertIn('color_fidelity',SETTING_NAMES)

    def test_gartic_reducer_retains_bright_anchor(self):
        palette=[(5,5,5),(90,30,30),(120,80,40),(150,100,70),(245,220,180),(80,130,170)]
        groups=[[(0,0,20,0)],[(0,1,30,1)],[(0,2,25,2)],[(0,3,20,3)],[(0,4,2,4)],[(0,5,15,5)]]
        _result,meta=optimize_gartic_phone_groups(groups,palette,max_colors=4,color_fidelity='Faithful')
        self.assertIn(meta['brightest_color_index'],meta['kept_color_indexes'])
        self.assertIn(meta['darkest_color_index'],meta['kept_color_indexes'])

    def test_validate(self):
        self.assertEqual(validate_color_fidelity('Faithful'),'Faithful')
        with self.assertRaises(ValueError):validate_color_fidelity('Moody')

if __name__=='__main__':
    unittest.main()
