import unittest
from PIL import Image,ImageDraw
from GarticSketchPaths import trace_contours
from DrawBot import make_plan

class GarticSketchTests(unittest.TestCase):
    def render(self,im):
        paths,meta=trace_contours(im)
        out=Image.new('L',im.size,255);d=ImageDraw.Draw(out)
        for p in paths:
            if len(p)==1:d.point(p[0],fill=0)
            else:d.line(p,fill=0,width=1)
        return out,paths
    def test_diagonal_is_one_path_and_two_points(self):
        im=Image.new('L',(80,80),255);ImageDraw.Draw(im).line((5,5,70,70),fill=0)
        out,paths=self.render(im)
        self.assertEqual(out.tobytes(),im.tobytes());self.assertEqual(len(paths),1);self.assertEqual(len(paths[0]),2)
    def test_curves_loops_branches_and_isolated_points_preserve_raster(self):
        im=Image.new('L',(160,120),255);d=ImageDraw.Draw(im)
        d.ellipse((10,10,65,85),outline=0);d.line((90,15,90,100),fill=0);d.line((70,45,140,45),fill=0);d.point((150,110),fill=0)
        out,paths=self.render(im);self.assertEqual(out.tobytes(),im.tobytes())
    def test_no_bridge_between_disconnected_shapes(self):
        im=Image.new('L',(40,40),255);d=ImageDraw.Draw(im);d.line((2,2,12,12),fill=0);d.line((18,18,35,35),fill=0)
        out,paths=self.render(im);self.assertEqual(len(paths),2);self.assertEqual(out.tobytes(),im.tobytes())
    def test_empty_and_cancellation(self):
        self.assertEqual(trace_contours(Image.new('L',(20,20),255))[0],[])
        with self.assertRaises(InterruptedError):trace_contours(Image.new('L',(20,20)),lambda:True)
    def test_split_paths_share_endpoints_and_preserve_raster(self):
        im=Image.new('L',(60,60),255);ImageDraw.Draw(im).ellipse((5,5,50,50),outline=0)
        paths,_=trace_contours(im,max_points=5)
        self.assertTrue(all(len(p)<=5 for p in paths))
        out=Image.new('L',im.size,255)
        for p in paths:ImageDraw.Draw(out).line(p,fill=0)
        self.assertEqual(out.tobytes(),im.tobytes())
    def test_gartic_only_fewer_paths_and_preserved_contours(self):
        im=Image.new('RGB',(160,120),'white');d=ImageDraw.Draw(im);d.ellipse((15,10,90,100),fill='red');d.polygon([(105,20),(145,100),(100,100)],fill='blue')
        opts=dict(outline=True,paint_current_color=True,detail=8,delay=.01,contrast=1,brush_px=1,max_seconds=180,lines=True)
        old=make_plan(im,im.size,dict(opts,profile_key='other'))
        for key in ('gartic-io','gartic-phone'):
            new=make_plan(im,im.size,dict(opts,profile_key=key))
            self.assertIn('gartic_sketch_meta',new['options'])
            self.assertLess(sum(map(len,new['execution_groups'])),sum(map(len,old['execution_groups'])))
            # Previous serpentine connectors can thicken corners. Compare coverage
            # against the source contour, allowing the preview's half-pixel transform.
            import numpy as np
            from PIL import ImageFilter,ImageOps
            ink=ImageOps.invert(new['preview'].convert('L')).filter(ImageFilter.MaxFilter(3))
            expected=np.asarray(new['image'].convert('L'))==0
            self.assertTrue(np.all(np.asarray(ink)[expected]>0))
            self.assertLessEqual(np.sum(np.asarray(new['preview'].convert('L'))==0),np.sum(np.asarray(old['preview'].convert('L'))==0))

    def test_runtime_keeps_planned_contour_priority(self):
        import threading
        from unittest.mock import patch
        from test_drawbot import Mouse,NoWait,options
        from DrawBot import execute_plan
        im=Image.new('RGB',(80,80),'white');ImageDraw.Draw(im).ellipse((10,10,60,60),outline='black',width=3)
        plan=make_plan(im,im.size,dict(options(),outline=True,paint_current_color=True,profile_key='gartic-phone',brush_px=1))
        mouse=Mouse()
        with patch('DrawBot.order_paths',side_effect=AssertionError('Do not reorder Gartic contour priority')):
            execute_plan(plan,(100,100,80,80),(),mouse,NoWait(),threading.Event(),lambda *a:None)
        self.assertFalse(mouse.held)
