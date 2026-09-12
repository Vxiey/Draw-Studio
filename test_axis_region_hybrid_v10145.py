import unittest
from PIL import Image,ImageDraw
from AxisRegionPlanner import horizontal_components,regional_axis_variants
from GarticSketchPaths import trace_contours


def raster_runs(runs,size=(128,128)):
    image=Image.new('1',size)
    draw=ImageDraw.Draw(image)
    for run in runs:draw.line(run,fill=1,width=1)
    return image.tobytes()


def raster_paths(paths,size=(128,128)):
    image=Image.new('1',size)
    draw=ImageDraw.Draw(image)
    for path in paths:
        if len(path)==1:draw.point(path[0],fill=1)
        else:draw.line(path,fill=1,width=1)
    return image.tobytes()


class AxisRegionHybridTests(unittest.TestCase):
    def test_connected_regions_get_lossless_mixed_axis_candidate(self):
        runs=[]
        # Wide region: horizontal is already cheap.
        runs.extend((5,y,50,y) for y in range(5,10))
        # Tall region: vertical is much cheaper.
        runs.extend((80,y,84,y) for y in range(20,90))
        self.assertEqual(len(horizontal_components(runs)),2)
        variants=regional_axis_variants(runs)
        self.assertTrue(variants)
        best=min(variants,key=lambda item:item[1]['raw_run_delta'])
        self.assertLess(best[1]['raw_run_delta'],0)
        self.assertEqual(raster_runs(best[0]),raster_runs(runs))
        self.assertTrue(any(x0==x1 for x0,y0,x1,y1 in best[0]))
        self.assertTrue(any(y0==y1 for x0,y0,x1,y1 in best[0]))

    def test_diagonal_component_classification_never_bridges_pixels(self):
        runs=[(i,i,i,i) for i in range(20)]
        self.assertEqual(len(horizontal_components(runs,adjacency=1)),1)
        self.assertEqual(len(horizontal_components(runs,adjacency=0)),20)

    def test_dense_sketch_uses_axis_fallback_and_preserves_exact_raster(self):
        image=Image.new('L',(128,128),255)
        ImageDraw.Draw(image).rectangle((10,15,100,95),fill=0)
        paths,meta=trace_contours(image)
        self.assertGreater(meta['axis_components'],0)
        expected=Image.new('1',image.size)
        src=ImageDraw.Draw(expected);src.rectangle((10,15,100,95),fill=1)
        self.assertEqual(raster_paths(paths,image.size),expected.tobytes())
        self.assertGreater(meta['dense_axis_shortcuts'],0)

    def test_thin_sketch_keeps_contour_tracer(self):
        image=Image.new('L',(128,128),255)
        ImageDraw.Draw(image).line((5,5,110,110),fill=0)
        paths,meta=trace_contours(image)
        self.assertEqual(meta['axis_components'],0)
        self.assertEqual(len(paths),1)
        expected=Image.new('1',image.size);ImageDraw.Draw(expected).line((5,5,110,110),fill=1)
        self.assertEqual(raster_paths(paths,image.size),expected.tobytes())

if __name__=='__main__':unittest.main()
