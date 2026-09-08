import unittest
import numpy as np
from PIL import Image, ImageDraw
from Colors import allColors
from PixelAccuratePlanner import build_pixel_map
from PixelStrokeEngine import build_pixel_stroke_plan
from ShadowDetailEngine import analyze_shadow_contours


class ShadowContourV10112Tests(unittest.TestCase):
    def test_local_shadow_and_contour_maps_detect_structure(self):
        rgb=np.full((40,60,3),220,dtype=np.uint8)
        rgb[10:31,15:45]=120
        rgb[18:25,24:38]=55
        draw=np.ones((40,60),bool)
        idx=np.zeros((40,60),np.int16);idx[10:31,15:45]=1;idx[18:25,24:38]=2
        edges=np.zeros((40,60),np.float32)
        edges[:,14:16]=1;edges[:,44:46]=1
        out=analyze_shadow_contours(rgb,idx,draw,edges)
        self.assertEqual(out['shadow_map'].shape,(40,60))
        self.assertGreater(float(out['shadow_map'][20,28]),float(out['shadow_map'][2,2]))
        self.assertGreater(float(out['contour_map'].max()),.5)
        self.assertGreater(out['metadata']['shadow_detail_pixels'],0)

    def test_pixel_map_exposes_shadow_contour_metadata(self):
        palette=tuple(c.RGB for c in allColors)
        im=Image.new('RGBA',(72,48),'white');d=ImageDraw.Draw(im)
        d.rectangle((8,8,60,40),fill=(180,150,120,255))
        d.rectangle((16,25,54,38),fill=(70,55,45,255))
        d.line((8,8,60,8),fill=(0,0,0,255),width=1)
        pm=build_pixel_map(im,palette,gpu_mode='CPU',skip_white=True)
        meta=pm.as_meta()
        self.assertTrue(meta['shadow_analysis'])
        self.assertTrue(meta['contour_analysis'])
        self.assertIsNotNone(pm.contour_map)
        self.assertIsNotNone(pm.shadow_detail_map)
        self.assertGreaterEqual(meta['contour_percent'],0)
        self.assertGreaterEqual(meta['shadow_detail_percent'],0)

    def test_stroke_plan_tags_render_roles_without_losing_paths(self):
        palette=tuple(c.RGB for c in allColors)
        im=Image.new('RGBA',(60,40),'white');d=ImageDraw.Draw(im)
        d.rectangle((5,5,50,34),fill=palette[8]+(255,))
        d.rectangle((5,24,50,34),fill=palette[0]+(255,))
        d.line((5,5,50,5),fill=palette[0]+(255,),width=1)
        pm=build_pixel_map(im,palette,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(palette),cpu_workers=2)
        meta=plan['metadata']
        self.assertIn('render_role_counts',meta)
        self.assertIn('post_processing',meta)
        self.assertEqual(meta['scheduled_paths'],len(plan['execution_sequence']))
        self.assertTrue(all('render_role' in e for e in plan['execution_sequence']))

    def test_build_exe_includes_engine(self):
        from pathlib import Path
        src=(Path(__file__).parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'ShadowDetailEngine'",src)

if __name__=='__main__':unittest.main()
