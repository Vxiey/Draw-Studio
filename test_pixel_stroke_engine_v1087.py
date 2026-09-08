import unittest
import numpy as np
from PIL import Image

from PixelAccuratePlanner import PixelMap, build_pixel_map
from DrawBot import make_plan
from Colors import allColors
from PixelStrokeEngine import (connected_components, build_component_paths,
                               build_pixel_stroke_plan, classify_component, PHASES)


def pixelmap_from_index(index, *, protected=None, importance=None, edges=None):
    idx=np.asarray(index,dtype=np.int16)
    h,w=idx.shape
    drawable=idx>=0
    safe_idx=np.where(drawable,idx,0).astype(np.int16)
    rgb=np.zeros((h,w,3),dtype=np.uint8)
    rgb[drawable]=np.stack([(safe_idx[drawable]*61)%255,(safe_idx[drawable]*97)%255,(safe_idx[drawable]*37)%255],axis=1)
    if protected is None: protected=np.zeros((h,w),dtype=bool)
    if importance is None: importance=np.where(drawable,.2,0).astype(np.float32)
    if edges is None: edges=np.where(drawable,.1,0).astype(np.float32)
    return PixelMap(w,h,rgb,safe_idx,drawable,np.asarray(edges,dtype=np.float32),
                    np.asarray(importance,dtype=np.float32),np.asarray(protected,dtype=bool),{})


def rasterize_path(path):
    pts=set()
    if not path:return pts
    pts.add(tuple(path[0]))
    for a,b in zip(path,path[1:]):
        x0,y0=a;x1,y1=b
        if x0==x1:
            for y in range(min(y0,y1),max(y0,y1)+1):pts.add((x0,y))
        elif y0==y1:
            for x in range(min(x0,x1),max(x0,x1)+1):pts.add((x,y0))
        else:
            raise AssertionError('Pixel Stroke Engine generated a diagonal connector')
    return pts


class PixelStrokeEngineTests(unittest.TestCase):
    def test_four_connected_regions_do_not_join_across_blank_gap(self):
        pm=pixelmap_from_index([[1,1,-1,1,1],[1,1,-1,1,1]])
        comps,cmap,meta=connected_components(pm)
        self.assertEqual(len(comps),2)
        self.assertEqual(meta['component_connectivity'],4)
        self.assertNotEqual(int(cmap[0,0]),int(cmap[0,4]))

    def test_diagonal_touch_is_not_a_component_merge(self):
        pm=pixelmap_from_index([[2,-1],[-1,2]])
        comps,_,_=connected_components(pm)
        self.assertEqual(len(comps),2)

    def test_local_orientation_prefers_vertical_for_tall_component(self):
        pm=pixelmap_from_index([[3],[3],[3],[3],[3],[3]])
        comps,cmap,_=connected_components(pm)
        paths,meta=build_component_paths(comps[0],cmap)
        self.assertEqual(meta['orientation'],'vertical')
        self.assertEqual(len(paths),1)

    def test_local_orientation_prefers_horizontal_for_wide_component(self):
        pm=pixelmap_from_index([[3,3,3,3,3,3]])
        comps,cmap,_=connected_components(pm)
        _,meta=build_component_paths(comps[0],cmap)
        self.assertEqual(meta['orientation'],'horizontal')

    def test_safe_merge_never_paints_outside_component(self):
        pm=pixelmap_from_index([
            [1,1,1,-1,-1],
            [1,1,-1,-1,-1],
            [1,1,1,1,-1],
        ])
        comps,cmap,_=connected_components(pm)
        comp=comps[0]
        paths,_=build_component_paths(comp,cmap)
        covered=set().union(*(rasterize_path(p) for p in paths))
        target={(x,y) for y in range(pm.height) for x in range(pm.width) if int(cmap[y,x])==comp.component_id}
        self.assertEqual(covered,target)

    def test_protected_tiny_component_becomes_cleanup(self):
        protected=np.zeros((5,5),bool);protected[2,2]=True
        importance=np.zeros((5,5),np.float32);importance[2,2]=.95
        edges=np.zeros((5,5),np.float32);edges[2,2]=.95
        idx=np.full((5,5),-1);idx[2,2]=1
        pm=pixelmap_from_index(idx,protected=protected,importance=importance,edges=edges)
        comps,_,_=connected_components(pm)
        self.assertEqual(classify_component(comps[0],1),'cleanup')

    def test_large_flat_component_becomes_fill(self):
        idx=np.ones((30,30),dtype=int)
        pm=pixelmap_from_index(idx,importance=np.full((30,30),.08,np.float32),edges=np.full((30,30),.03,np.float32))
        comps,_,_=connected_components(pm)
        self.assertEqual(classify_component(comps[0],900),'fill')

    def test_four_pass_sequence_is_monotonic(self):
        palette=[(255,255,255),(0,0,0),(255,0,0),(0,0,255)]
        image=Image.new('RGB',(48,32),'white')
        px=image.load()
        for y in range(2,26):
            for x in range(2,28):px[x,y]=(255,0,0)
        for y in range(5,27):px[35,y]=(0,0,255)
        px[41,10]=(0,0,0);px[42,10]=(0,0,0)
        pm=build_pixel_map(image,palette,skip_white=True,gpu_mode='CPU')
        plan=build_pixel_stroke_plan(pm,len(palette))
        order={p:i for i,p in enumerate(PHASES)}
        seen=[order[e['phase']] for e in plan['execution_sequence']]
        self.assertEqual(seen,sorted(seen))
        self.assertTrue(plan['metadata']['multi_pass'])

    def test_execution_paths_preserve_exact_palette_coverage(self):
        pm=pixelmap_from_index([
            [1,1,1,-1,2,2],
            [1,1,-1,-1,2,2],
            [1,1,1,1,2,-1],
            [-1,-1,3,3,3,3],
        ])
        plan=build_pixel_stroke_plan(pm,4)
        for color,paths in enumerate(plan['execution_groups']):
            covered=set().union(*(rasterize_path(p) for p in paths)) if paths else set()
            target={(x,y) for y in range(pm.height) for x in range(pm.width)
                    if pm.drawable_mask[y,x] and int(pm.palette_index[y,x])==color}
            self.assertEqual(covered,target)

    def test_component_scheduler_metadata_is_present(self):
        pm=pixelmap_from_index([[1,1,-1,2],[1,1,-1,2],[3,3,3,2]])
        plan=build_pixel_stroke_plan(pm,4)
        meta=plan['metadata']
        self.assertEqual(meta['engine'],'Pixel Stroke Engine Block B')
        self.assertEqual(meta['scheduler_backend'],'cpu-component-bounded-nearest')
        self.assertTrue(meta['connected_regions'])
        self.assertTrue(meta['local_orientation'])
        self.assertTrue(meta['safe_component_merge'])
        self.assertEqual(meta['scheduled_paths'],len(plan['execution_sequence']))

    def test_drawbot_uses_component_engine_and_four_pass_sequence(self):
        palette=tuple(c.RGB for c in allColors)
        image=Image.new('RGBA',(24,18),'white')
        px=image.load()
        for y in range(2,14):
            for x in range(2,13):px[x,y]=palette[2]+(255,)
        for y in range(4,16):px[18,y]=palette[8]+(255,)
        px[20,7]=(0,0,0,255)
        options=dict(detail=10,delay=.001,speed='Balanced',precision='Ultra',lines=True,
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
        plan=make_plan(image,(96,72),options)
        self.assertTrue(plan['path_stats']['pixel_component_engine'])
        self.assertEqual(plan['path_stats']['mode'],'Pixel Accurate component paths')
        self.assertTrue(plan['execution_sequence'])
        self.assertEqual(plan['path_stats']['progressive_phase_order'],'fill -> mid detail -> fine detail -> cleanup')
        self.assertEqual(plan['count'],len(plan['execution_sequence']))
        self.assertEqual(plan['options']['pixel_stroke_meta']['engine'],'Pixel Stroke Engine Block B')
        self.assertNotIn('gartic_phone_direct_paths',plan['options'])

    def test_release_build_includes_block_b_engine(self):
        from pathlib import Path
        source=(Path(__file__).parent/'build_exe.py').read_text(encoding='utf-8')
        self.assertIn("'--hidden-import', 'PixelStrokeEngine'",source)


if __name__=='__main__':unittest.main()
