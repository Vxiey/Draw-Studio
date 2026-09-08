import unittest
from unittest import mock
from types import SimpleNamespace
import numpy as np
from PIL import Image, ImageDraw

from Colors import allColors
from PixelAccuratePlanner import build_pixel_map
from PixelStrokeEngine import build_pixel_stroke_plan
from PixelAccuracyGpu import compile_swept_rectangles, _plan
from PixelAccuracyEngine import (simulate_strokes, progressive_time_budget,
                                 progressive_accuracy_checkpoints, refine_with_corrections)
from ProfileEngine import resolve_profile_policy
from DrawBot import make_plan
from test_pixel_accurate_v1086 import opts


def entry(color, path, phase='fine_detail', protected=False, serial=0):
    return {'color_index':color,'path':tuple(path),'phase':phase,'protected':protected,
            'importance':1.0 if protected else .3,'serial':serial}


class PixelPerformanceV1089Tests(unittest.TestCase):
    def setUp(self):
        self.palette=tuple(c.RGB for c in allColors)

    def test_01_swept_rectangle_compiler_matches_square_brush_geometry(self):
        seq=[entry(2,((1,2),(4,2)))]
        r=compile_swept_rectangles(seq,3,8,6)
        self.assertEqual(r.shape,(1,5))
        self.assertEqual(tuple(r[0]),(0,1,5,3,2))

    def test_02_simulator_accepts_cuda_backend_result(self):
        im=Image.new('RGBA',(4,2),self.palette[2]+(255,))
        pm=build_pixel_map(im,self.palette,gpu_mode='CPU',skip_white=False)
        sim=np.full((2,4),2,dtype=np.int16);counts=np.ones((2,4),dtype=np.uint16)
        fake=(sim,counts,{'simulation_backend':'cuda-cupy-tiled-raster','tile_rows':2,'vram_budget_mb':8000})
        with mock.patch('PixelAccuracyGpu.simulate_cuda',return_value=fake), \
             mock.patch('PixelAccuracyGpu.score_cuda_host',return_value=None):
            result=simulate_strokes(pm,[entry(2,((0,0),(3,0)))],self.palette,gpu_mode='NVIDIA CUDA')
        self.assertEqual(result.metrics['simulation_backend'],'cuda-cupy-tiled-raster')
        self.assertEqual(result.metrics['pixel_accuracy_percent'],100.0)

    def test_03_vram_plan_selects_bounded_tiles_and_batches(self):
        info=SimpleNamespace(vram_budget_mb=512,free_vram_mb=512)
        with mock.patch('GpuAcceleration.plan_vram_allocation',return_value={'tile_rows':128}):
            p=_plan(info,1920,1080,900000)
        self.assertEqual(p.tile_rows,128)
        self.assertGreater(p.tile_count,1)
        self.assertLessEqual(p.rectangle_batch_size,250000)
        self.assertGreater(p.rectangle_batches,1)

    def test_04_parallel_region_processing_is_reported(self):
        im=Image.new('RGBA',(96,64),'white');d=ImageDraw.Draw(im)
        # many disconnected same-colour islands -> >16 components
        for y in range(2,60,8):
            for x in range(2,92,10):d.rectangle((x,y,x+2,y+2),fill=self.palette[2]+(255,))
        pm=build_pixel_map(im,self.palette,gpu_mode='CPU',skip_white=True)
        plan=build_pixel_stroke_plan(pm,len(self.palette),cpu_workers=4)
        m=plan['metadata']
        self.assertGreaterEqual(m['component_count'],16)
        self.assertEqual(m['component_path_backend'],'cpu-parallel-components')
        self.assertEqual(m['vertical_run_backend'],'cpu-parallel-column-chunks')

    def test_05_time_budget_limits_paths_without_changing_source_sequence(self):
        seq=[entry(2,((i,0),),phase='fill',serial=i) for i in range(120)]
        r=progressive_time_budget(seq,active=True,seconds=10,profile_key='gartic-phone')
        self.assertTrue(r['active']);self.assertLess(r['base_path_budget'],len(seq))
        self.assertEqual(len(seq),120)  # input remains untouched
        self.assertGreater(r['correction_reserve'],0)

    def test_06_tight_budget_reserves_protected_cleanup(self):
        seq=[];serial=0
        for phase,count in [('fill',40),('mid_detail',40),('cleanup',20),('fine_detail',40)]:
            for _ in range(count):
                seq.append(entry(2,((serial%20,serial//20),),phase=phase,protected=(phase=='cleanup'),serial=serial));serial+=1
        r=progressive_time_budget(seq,active=True,seconds=10,profile_key='gartic-phone')
        chosen=r['execution_sequence']
        self.assertTrue(any(e['phase']=='cleanup' and e['protected'] for e in chosen))
        self.assertLessEqual(len(chosen),r['base_path_budget'])

    def test_07_corrections_respect_total_progressive_path_budget(self):
        im=Image.new('RGBA',(12,1),self.palette[2]+(255,))
        pm=build_pixel_map(im,self.palette,gpu_mode='CPU',skip_white=False)
        result=refine_with_corrections(pm,[],self.palette,brush_px=1,max_passes=2,max_total_paths=1)
        self.assertLessEqual(len(result['execution_sequence']),1)
        self.assertLessEqual(result['metadata']['correction_paths_added'],1)

    def test_08_progressive_accuracy_checkpoints_improve_on_disjoint_components(self):
        im=Image.new('RGBA',(8,1),'white');d=ImageDraw.Draw(im)
        d.rectangle((0,0,3,0),fill=self.palette[2]+(255,));d.rectangle((4,0,7,0),fill=self.palette[10]+(255,))
        pm=build_pixel_map(im,self.palette,gpu_mode='CPU',skip_white=False)
        seq=[entry(2,((0,0),(3,0)),phase='fill'),entry(10,((4,0),(7,0)),phase='fine_detail',serial=1)]
        cps=progressive_accuracy_checkpoints(pm,seq,self.palette,brush_px=1)
        self.assertEqual(len(cps),2)
        self.assertLess(cps[0]['pixel_accuracy_percent'],cps[-1]['pixel_accuracy_percent'])
        self.assertEqual(cps[-1]['pixel_accuracy_percent'],100.0)

    def test_09_pixel_accurate_auto_policy_preserves_explicit_timer(self):
        requested={'draw_quality':'Pixel Accurate','quality':'Maximum detail','planning_resolution':'Extreme',
                   'background_simplification':'Off','color_grouping':'Accurate','stroke_optimizer':'Travel only',
                   'adaptive_detail':'Off','time_budget_mode':'60 sec','target_stroke_count':'Auto','max_stroke_cap':'Unlimited',
                   'progressive_rendering':'On','color_rendering':'Perceptual match','mode':'Smart paths (recommended)',
                   'shape_model':'Better shapes v2','shape_order':'Fill first','speed':'Balanced','precision':'Ultra',
                   'visual_verification':'Off','color_workflow':'Finish color first','color_layers':'Off',
                   'custom_color_workflow':'Calibrated palette','exact_color_limit':'Auto','planning_watchdog':'On',
                   'resource_scheduler':'Auto','background_fill':'Off','fill_engine':'Auto','edge_behavior':'Hard Clip'}
        effective,_=resolve_profile_policy('Gartic Phone',requested,mode='Auto')
        self.assertEqual(effective['time_budget_mode'],'60 sec')
        self.assertEqual(effective['draw_quality'],'Pixel Accurate')
        self.assertEqual(effective['adaptive_detail'],'Off')

    def test_10_drawbot_exposes_block_d_progressive_and_parallel_metadata(self):
        im=Image.new('RGBA',(40,24),self.palette[2]+(255,))
        plan=make_plan(im,(160,96),opts(cpu_workers='4',time_budget_mode='30 sec',gpu_mode='CPU'))
        meta=plan['options']['pixel_accuracy_meta'];stroke=plan['options']['pixel_stroke_meta']
        self.assertEqual(meta['engine'],'Pixel Accuracy Engine Block D')
        self.assertTrue(meta['block_d'])
        self.assertTrue(meta['progressive_time_budget']['active'])
        self.assertIn('accuracy_checkpoints',meta)
        self.assertIn('component_path_backend',stroke)


if __name__=='__main__':unittest.main()
