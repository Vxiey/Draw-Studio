import unittest
import numpy as np
from PIL import Image, ImageDraw

from DetailFidelityPlanner import apply_detail_fidelity_policy
from PixelAccuratePlanner import build_pixel_map, micro_detail_map


class Step26DetailFidelityTests(unittest.TestCase):
    def test_pixel_accurate_policy_disables_destructive_simplification(self):
        out, meta = apply_detail_fidelity_policy({
            'draw_quality':'Pixel Accurate','outline':False,
            'adaptive_detail':'Strong simplify','background_simplification':'Strong',
            'color_grouping':'Reduced palette','stroke_optimizer':'Smart merge',
            'target_stroke_count_resolved':500,
        })
        self.assertTrue(meta['active'])
        self.assertEqual(out['adaptive_detail'],'Off')
        self.assertEqual(out['background_simplification'],'Off')
        self.assertEqual(out['color_grouping'],'Accurate')
        self.assertEqual(out['stroke_optimizer'],'Travel only')
        self.assertIsNone(out['target_stroke_count_resolved'])
        self.assertEqual(out['planning_resolution_effective'],'Pixel Accurate / full target')

    def test_non_pixel_mode_is_not_overridden(self):
        src={'draw_quality':'High likeness','adaptive_detail':'Strong simplify',
             'background_simplification':'Strong','color_grouping':'Reduced palette'}
        out, meta = apply_detail_fidelity_policy(src)
        self.assertFalse(meta['active'])
        self.assertEqual(out['adaptive_detail'],'Strong simplify')
        self.assertEqual(out['background_simplification'],'Strong')

    def test_micro_detail_scores_thin_palette_boundary(self):
        idx=np.zeros((9,9),dtype=np.int16)
        idx[4,4]=1
        drawable=np.ones((9,9),dtype=bool)
        edges=np.zeros((9,9),dtype=np.float32); edges[4,4]=1.0
        micro=micro_detail_map(idx,drawable,edges)
        self.assertGreater(float(micro[4,4]),.7)
        self.assertLess(float(micro[1,1]),.2)

    def test_pixel_map_reports_step26_and_protects_micro_feature(self):
        im=Image.new('RGB',(24,18),'white')
        d=ImageDraw.Draw(im)
        d.rectangle((4,4,19,14),fill=(180,180,180))
        d.point((12,9),fill=(0,0,0))
        pm=build_pixel_map(im,[(255,255,255),(180,180,180),(0,0,0)],
                           color_rendering='RGB nearest',color_fidelity='Exact',
                           skip_white=False,gpu_mode='CPU')
        self.assertEqual(pm.metadata['step'],26)
        self.assertTrue(pm.metadata['full_resolution'])
        self.assertEqual(pm.metadata['simplification_policy'],'lossless-only')
        self.assertIsNotNone(pm.micro_detail_map)
        self.assertTrue(bool(pm.protected_mask[9,12]))
        meta=pm.as_meta()
        self.assertIn('micro_detail_percent',meta)
        self.assertIn('analysis_backends',meta)

    def test_drawbot_integrates_step26_policy(self):
        from pathlib import Path
        text=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn('apply_detail_fidelity_policy',text)
        self.assertIn("options['detail_fidelity_meta']=step26_meta",text)
        build=Path('build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'DetailFidelityPlanner'",build)


if __name__=='__main__':
    unittest.main()
