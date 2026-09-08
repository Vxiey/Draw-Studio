import unittest
from pathlib import Path
import numpy as np
from PIL import Image

from PixelAccuratePlanner import PixelMap, build_pixel_map
from PixelAccuracyEngine import (
    simulate_strokes, refine_with_corrections, execution_groups_from_sequence,
    ERROR_MISSING, ERROR_WRONG_COLOR, ERROR_SPILL, render_coverage_map, render_error_map)
from PixelStrokeEngine import build_pixel_stroke_plan
from DrawBot import make_plan
from Colors import allColors


def pm_from_index(index, *, protected=None, edges=None, importance=None):
    idx=np.asarray(index,dtype=np.int16)
    h,w=idx.shape
    drawable=idx>=0
    safe=np.where(drawable,idx,0).astype(np.int16)
    rgb=np.zeros((h,w,3),dtype=np.uint8)
    if protected is None:protected=np.zeros((h,w),bool)
    if edges is None:edges=np.where(drawable,.1,0).astype(np.float32)
    if importance is None:importance=np.where(drawable,.2,0).astype(np.float32)
    return PixelMap(w,h,rgb,safe,drawable,np.asarray(edges,np.float32),np.asarray(importance,np.float32),np.asarray(protected,bool),{})


def entry(color,path,phase='fine_detail'):
    return {'color_index':color,'path':tuple(path),'phase':phase,'phase_label':phase,'component_id':0,'orientation':'horizontal','serial':0}


def options(**changes):
    base=dict(detail=10,delay=.001,speed='Balanced',precision='Ultra',lines=True,
              drawing_mode='Smart paths (recommended)',smart_paths=True,render_style='Standard / pixel',
              draw_quality='Pixel Accurate',human_mode='Off',gpu_mode='CPU',gpu_vram='Auto',
              gpu_performance='High throughput',cpu_workers='4',cpu_engine='Threads',ram_budget='2 GB',
              ram_custom_mb='2048',planning_resolution='Extreme',resource_scheduler='Off',background_fill='Off',
              background_simplification='Off',color_grouping='Accurate',color_workflow='Progressive passes',
              stroke_optimizer='Travel only',adaptive_detail='Off',visual_verification='Off',
              color_rendering='Perceptual match',color_layers='Off',custom_color_workflow='Calibrated palette',
              exact_color_limit='Auto',tool_strategy='Auto',portrait_focus=True,skip_white=True,contrast=1.0,
              outline=False,brush_px=1,max_seconds=600,manual_max_seconds=600,time_budget_mode='Manual',
              target_stroke_count='Auto',target_stroke_custom='2500',paint_current_color=False,erase_mode=False,
              paint_tool='Use current tool',effective_paint_tool='Use current tool',tool_actions=[],
              fill_tool_available=False,fill_tool_actions=[],fill_restore_actions=[])
    base.update(changes);return base


class PixelAccuracyEngineV1088Tests(unittest.TestCase):
    def setUp(self):
        self.palette=((255,255,255),(0,0,0),(255,0,0),(0,0,255))

    def test_exact_brush1_sequence_scores_100_percent(self):
        pm=pm_from_index([[1,1,1],[-1,2,2]])
        seq=[entry(1,((0,0),(2,0))),entry(2,((1,1),(2,1)))]
        r=simulate_strokes(pm,seq,self.palette,brush_px=1)
        self.assertEqual(r.metrics['pixel_accuracy_percent'],100.0)
        self.assertEqual(r.metrics['coverage_percent'],100.0)
        self.assertEqual(r.metrics['error_pixels'],0)

    def test_coverage_map_tracks_every_touched_pixel(self):
        pm=pm_from_index([[1,1,1],[-1,-1,-1]])
        r=simulate_strokes(pm,[entry(1,((0,0),(2,0)))],self.palette,brush_px=1)
        self.assertEqual(int(np.count_nonzero(r.coverage_map)),3)
        self.assertTrue(np.all(r.coverage_map[0]))

    def test_error_map_distinguishes_missing_wrong_and_spill(self):
        pm=pm_from_index([[1,1,-1],[2,-1,-1]])
        seq=[entry(2,((0,0),)),entry(1,((2,0),))]
        r=simulate_strokes(pm,seq,self.palette,brush_px=1)
        self.assertEqual(int(r.error_map[0,1]),ERROR_MISSING)
        self.assertEqual(int(r.error_map[0,0]),ERROR_WRONG_COLOR)
        self.assertEqual(int(r.error_map[0,2]),ERROR_SPILL)

    def test_brush_width_simulation_detects_spill(self):
        pm=pm_from_index([[-1,-1,-1],[-1,1,-1],[-1,-1,-1]])
        r=simulate_strokes(pm,[entry(1,((1,1),))],self.palette,brush_px=3)
        self.assertGreater(r.metrics['spill_pixels'],0)
        self.assertLess(r.metrics['pixel_accuracy_percent'],100.0)

    def test_correction_pass_repairs_incomplete_brush1_plan(self):
        pm=pm_from_index([[1,1,1,1]])
        result=refine_with_corrections(pm,[entry(1,((0,0),(1,0)))],self.palette,brush_px=1,max_passes=2)
        self.assertEqual(result['metadata']['final_accuracy_percent'],100.0)
        self.assertGreater(result['metadata']['correction_paths_added'],0)
        self.assertEqual(result['metadata']['correction_passes_accepted'],1)
        self.assertTrue(any(e['phase']=='correction_1' for e in result['execution_sequence']))

    def test_protected_accuracy_is_measured_separately(self):
        protected=np.array([[False,True]],bool)
        edges=np.array([[.1,.95]],np.float32)
        pm=pm_from_index([[1,1]],protected=protected,edges=edges)
        r=simulate_strokes(pm,[entry(1,((0,0),))],self.palette,brush_px=1)
        self.assertEqual(r.metrics['protected_accuracy_percent'],0.0)
        self.assertGreater(r.metrics['edge_pixels'],0)

    def test_correction_sequence_rebuilds_execution_groups(self):
        pm=pm_from_index([[1,1,1]])
        result=refine_with_corrections(pm,[entry(1,((0,0),))],self.palette,brush_px=1)
        groups=execution_groups_from_sequence(result['execution_sequence'],len(self.palette))
        self.assertEqual(sum(len(g) for g in groups),len(result['execution_sequence']))

    def test_diagnostic_images_match_pixelmap_size(self):
        pm=pm_from_index([[1,1],[-1,2]])
        r=simulate_strokes(pm,[entry(1,((0,0),(1,0))),entry(2,((1,1),))],self.palette,brush_px=1)
        self.assertEqual(render_coverage_map(pm,r).size,(2,2))
        self.assertEqual(render_error_map(pm,r).size,(2,2))

    def test_block_b_plan_is_simulated_losslessly_with_brush1(self):
        pm=pm_from_index([[1,1,-1,2],[1,1,-1,2],[3,3,3,2]])
        plan=build_pixel_stroke_plan(pm,4)
        r=simulate_strokes(pm,plan['execution_sequence'],self.palette,brush_px=1)
        self.assertEqual(r.metrics['target_color_accuracy_percent'],100.0)
        self.assertEqual(r.metrics['coverage_percent'],100.0)

    def test_drawbot_exposes_block_c_score_and_preview_maps(self):
        palette=tuple(c.RGB for c in allColors)
        image=Image.new('RGBA',(20,14),'white')
        px=image.load()
        for y in range(2,10):
            for x in range(2,11):px[x,y]=palette[2]+(255,)
        px[14,6]=(0,0,0,255)
        plan=make_plan(image,(80,56),options())
        meta=plan['options']['pixel_accuracy_meta']
        self.assertEqual(meta['engine'],'Pixel Accuracy Engine Block D')
        self.assertIn('coverage',plan['ui_previews'])
        self.assertIn('accuracy_error',plan['ui_previews'])
        self.assertGreaterEqual(plan['path_stats']['pixel_accuracy_percent'],0.0)
        self.assertEqual(plan['options']['pixel_stroke_engine'],'Block B + C + D + Shadow/Contour + Adaptive Brush v2')

    def test_release_build_includes_block_c_engine(self):
        source=(Path(__file__).parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'PixelAccuracyEngine'",source)


if __name__=='__main__':unittest.main()
