import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from PixelAccuratePlanner import build_pixel_map, groups_from_pixel_map
from ProfileEngine import resolve_profile_policy
from DrawBot import make_plan
from Colors import allColors


def opts(**changes):
    base=dict(detail=10,delay=.001,speed='Balanced',precision='Ultra',lines=True,
              drawing_mode='Smart paths (recommended)',smart_paths=True,
              render_style='Standard / pixel',draw_quality='Pixel Accurate',human_mode='Off',
              gpu_mode='CPU',gpu_vram='Auto',gpu_performance='High throughput',
              cpu_workers='4',cpu_engine='Threads',ram_budget='2 GB',ram_custom_mb='2048',
              planning_resolution='Extreme',resource_scheduler='Off',background_fill='Off',
              background_simplification='Off',color_grouping='Accurate',color_workflow='Finish color first',
              stroke_optimizer='Travel only',adaptive_detail='Off',visual_verification='Off',
              color_rendering='Perceptual match',color_layers='Off',custom_color_workflow='Calibrated palette',
              exact_color_limit='Auto',tool_strategy='Auto',portrait_focus=True,skip_white=False,
              contrast=1.0,outline=False,brush_px=1,max_seconds=600,manual_max_seconds=600,
              time_budget_mode='Manual',target_stroke_count='Auto',target_stroke_custom='2500',
              paint_current_color=False,erase_mode=False,paint_tool='Use current tool',
              effective_paint_tool='Use current tool',tool_actions=[],fill_tool_available=False,
              fill_tool_actions=[],fill_restore_actions=[])
    base.update(changes); return base


class PixelAccurateV1086Tests(unittest.TestCase):
    def setUp(self):
        self.palette=tuple(c.RGB for c in allColors)
        self.image=Image.new('RGBA',(64,40),'white')
        d=ImageDraw.Draw(self.image)
        d.rectangle((4,5,30,30),fill=self.palette[2]+(255,))
        d.rectangle((37,8,58,32),fill=self.palette[10]+(255,))
        d.point((33,20),fill=(0,0,0,255))

    def test_pixel_map_preserves_full_input_resolution(self):
        pm=build_pixel_map(self.image,self.palette,gpu_mode='CPU',skip_white=False)
        self.assertEqual((pm.width,pm.height),self.image.size)
        self.assertEqual(pm.palette_index.shape,(40,64))
        self.assertEqual(pm.edge_map.shape,(40,64))
        self.assertEqual(pm.importance_map.shape,(40,64))
        self.assertEqual(pm.protected_mask.shape,(40,64))

    def test_palette_mapping_is_deterministic_and_exact_for_palette_colours(self):
        pm=build_pixel_map(self.image,self.palette,gpu_mode='CPU',skip_white=False,color_rendering='Perceptual match')
        self.assertEqual(int(pm.palette_index[10,10]),2)
        self.assertEqual(int(pm.palette_index[15,45]),10)
        self.assertEqual(int(pm.palette_index[20,33]),0)
        self.assertEqual(pm.metadata['palette_backend'],'cpu-numpy')

    def test_edge_importance_and_tiny_feature_protection_exist(self):
        pm=build_pixel_map(self.image,self.palette,gpu_mode='CPU',skip_white=False)
        self.assertGreater(float(pm.edge_map.max()),0.5)
        self.assertGreater(float(pm.importance_map.max()),0.5)
        self.assertTrue(bool(pm.protected_mask[20,33]) or bool(pm.protected_mask[20,32]) or bool(pm.protected_mask[20,34]))

    def test_lossless_run_builder_reconstructs_palette_map(self):
        pm=build_pixel_map(self.image,self.palette,gpu_mode='CPU',skip_white=False)
        groups=groups_from_pixel_map(pm,len(self.palette),lines=True)
        rebuilt=np.full(pm.palette_index.shape,-1,dtype=np.int16)
        for ci,group in enumerate(groups):
            for x1,y1,x2,y2 in group:
                rebuilt[y1,x1:x2+1]=ci
        self.assertTrue(np.array_equal(rebuilt[pm.drawable_mask],pm.palette_index[pm.drawable_mask]))

    def test_auto_profile_policy_cannot_force_turbo_over_pixel_accurate(self):
        requested={
            'draw_quality':'Pixel Accurate','quality':'Maximum detail','planning_resolution':'Extreme',
            'background_simplification':'Off','color_grouping':'Accurate','stroke_optimizer':'Travel only',
            'adaptive_detail':'Off','time_budget_mode':'Manual','target_stroke_count':'Auto',
            'max_stroke_cap':'Unlimited','progressive_rendering':'On','color_rendering':'Perceptual match',
            'mode':'Smart paths (recommended)','shape_model':'Better shapes v2','shape_order':'Fill first',
            'speed':'Balanced','precision':'Ultra','visual_verification':'Off','color_workflow':'Finish color first',
            'color_layers':'Off','custom_color_workflow':'Calibrated palette','exact_color_limit':'Auto',
            'planning_watchdog':'On','resource_scheduler':'Auto','background_fill':'Off','fill_engine':'Auto','edge_behavior':'Hard Clip'
        }
        effective,meta=resolve_profile_policy('Gartic Phone',requested,mode='Auto')
        self.assertEqual(effective['draw_quality'],'Pixel Accurate')
        self.assertEqual(effective['planning_resolution'],'Extreme')
        self.assertEqual(effective['background_simplification'],'Off')
        self.assertEqual(effective['color_grouping'],'Accurate')
        self.assertEqual(effective['adaptive_detail'],'Off')
        self.assertEqual(effective['time_budget_mode'],'Manual')
        self.assertEqual(effective['max_stroke_cap'],'Unlimited')
        self.assertTrue(meta['applied'])

    def test_make_plan_uses_full_target_pixelmap_and_skips_destructive_stages(self):
        plan=make_plan(self.image,(320,200),opts())
        o=plan['options']; meta=o['pixel_map_meta']
        self.assertTrue(o['pixel_accurate'])
        self.assertEqual((meta['width'],meta['height']),(320,200))
        self.assertEqual(o['planner_max_pixels'],320*200)
        self.assertEqual(o['planning_resolution_effective'],'Pixel Accurate / full target')
        self.assertEqual(o['adaptive_detail'],'Off')
        self.assertEqual(o['background_simplification'],'Off')
        self.assertEqual(o['stroke_optimizer'],'Travel only')
        self.assertIsNone(o['target_stroke_count_resolved'])
        self.assertNotIn('gartic_phone_direct_paths',o)
        self.assertNotIn('real_speed_budget_meta',o)
        self.assertEqual(o['advanced_color_meta']['mode'],'pixel-accurate-map')
        self.assertGreater(plan['count'],0)

    def test_release_build_includes_new_engine(self):
        source=(Path(__file__).parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'PixelAccuratePlanner'",source)
        self.assertIn('numpy>=2.0,<3',(Path(__file__).parent/'requirements.txt').read_text())


if __name__=='__main__': unittest.main()
