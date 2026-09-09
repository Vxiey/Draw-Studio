import random
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
from ContinuousPaths import build_execution_paths
from ExtraFast2 import build_fast_paths, path_limits
from ExtraFast import select_fast_regions


def raster(paths):
    image=Image.new('1',(80,80))
    draw=ImageDraw.Draw(image)
    for path in paths:
        if len(path)==1:draw.point(path[0],fill=1)
        else:draw.line(path,fill=1,width=1)
    return image.tobytes()


def raster_large(paths,size=(420,420)):
    image=Image.new('1',size)
    draw=ImageDraw.Draw(image)
    for path in paths:
        if len(path)==1:draw.point(path[0],fill=1)
        else:draw.line(path,fill=1,width=1)
    return image.tobytes()


def region(**kw):
    return dict(dict(contour=[(0,0),(5,0),(5,5),(0,5),(0,0)],
                     color_index=0,stroke_cost_seconds=2,fill_cost_seconds=1,area_pixels=25),**kw)


class ExtraFastReviewTests(unittest.TestCase):
    def test_vertical_rectangle_joins_without_changing_pixels(self):
        group=[(x,2,x,60) for x in range(2,60)]
        paths,meta=build_fast_paths([group],{})
        self.assertLess(len(paths[0]),len(group))
        self.assertEqual(raster(paths[0]),raster([[(a,b),(c,d)] for a,b,c,d in group]))
        self.assertGreater(meta['vertical_colors_improved'],0)

    def test_adaptive_horizontal_limits_reduce_boundaries_losslessly(self):
        group=[(10,y,390,y) for y in range(10,350)]
        rows,points,_=path_limits({})
        baseline=build_execution_paths([group],enabled=True,max_rows_per_path=rows,max_points_per_path=points)
        paths,meta=build_fast_paths([group],{})
        self.assertLessEqual(len(paths[0]),len(baseline[0]))
        self.assertEqual(raster_large(paths[0]),raster_large([[(a,b),(c,d)] for a,b,c,d in group]))
        self.assertLessEqual(meta['intrinsic_cost_after_seconds'],meta['intrinsic_cost_before_seconds'])
        self.assertGreater(meta['adaptive_colors_improved'],0)
        self.assertGreater(meta['horizontal_colors_improved'],0)
        self.assertGreater(len(meta['candidate_path_limits']),1)

    def test_random_masks_holes_and_multiple_colors(self):
        rng=random.Random(44)
        for trial in range(80):
            groups=[[],[]]
            for x in range(2,60):
                for y in (2,25,50):
                    if rng.random()<.7:
                        groups[rng.randrange(2)].append((x,y,x,y+rng.randrange(1,20)))
            paths,_=build_fast_paths(groups,{})
            for source,result in zip(groups,paths):
                self.assertEqual(raster(result),raster([[(a,b),(c,d)] for a,b,c,d in source]))

    def test_horizontal_baseline_unchanged(self):
        groups=[[(2,y,60,y) for y in range(60)]]
        self.assertEqual(build_fast_paths(groups,{})[0],build_execution_paths(groups,enabled=True,max_rows_per_path=110,max_points_per_path=480))

    def test_mixed_axes_and_portrait_prefix(self):
        groups=[[(0,0,10,10)]+[(x,20,x,50) for x in range(20)]+[(30,y,60,y) for y in range(10)]]
        paths,_=build_fast_paths(groups,{},portrait_edge_count=1)
        self.assertEqual(tuple(paths[0][0]),((0,0),(10,10)))
        self.assertEqual(raster(paths[0]),raster([[(a,b),(c,d)] for a,b,c,d in groups[0]]))

    def test_cost_increase_keeps_baseline(self):
        class Model:
            def path_seconds(self,path):return len(path)**2
        groups=[[(x,0,x,20) for x in range(20)]]
        with patch('HybridCostModel.build_cost_model',return_value=Model()):
            paths,meta=build_fast_paths(groups,{})
        self.assertEqual(len(paths[0]),20)
        self.assertEqual(meta['vertical_colors_improved'],0)
        self.assertEqual(meta['adaptive_colors_improved'],0)

    def test_cancel(self):
        with self.assertRaises(InterruptedError):build_fast_paths([[(0,0,0,10)]],{},cancelled=lambda:True)

    def test_unlimited_overrides_stale_budget(self):
        for extra in ({'unlimited_time':True},{'time_budget_mode':'Unlimited / Accuracy'}):
            self.assertEqual(path_limits(dict(time_budget_active=True,max_seconds=30,**extra))[2],'quality-speed')

    def test_nonfinite_region_costs_rejected(self):
        for key in ('stroke_cost_seconds','fill_cost_seconds'):
            for value in (float('nan'),float('inf'),-float('inf')):
                self.assertFalse(select_fast_regions([region(**{key:value})],(10,10),(10,10),{})[0])

    def test_zero_ui_delay_and_batch_amortization(self):
        item=region(stroke_cost_seconds=1,fill_cost_seconds=.8)
        self.assertTrue(select_fast_regions([item],(10,10),(10,10),{'fill_tool_available':True,'ui_control_delay':0})[0])
        opts={'fill_tool_available':True,'ui_control_delay':.1}
        self.assertFalse(select_fast_regions([item],(10,10),(10,10),opts)[0])
        self.assertEqual(len(select_fast_regions([item]*3,(10,10),(10,10),opts)[0]),3)

    def test_legacy_cost_cancellation(self):
        calls=iter([False,False,True])
        item=region(stroke_cost_seconds=None,fill_cost_seconds=None,row_spans=[(y,0,5) for y in range(6)])
        with self.assertRaises(InterruptedError):
            select_fast_regions([item],(10,10),(10,10),{},lambda:next(calls,True))

if __name__=='__main__':unittest.main()
