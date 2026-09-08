import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from AutoSketchBudget import choose_sketch
from DrawBot import make_plan

class AutoSketchTests(unittest.TestCase):
    def test_selects_highest_detail_that_fits_with_margin(self):
        def planner(im,area,opts,cancelled):
            costs={'Detailed':93.8,'Balanced':58,'Simple':40}
            return {'options':dict(opts),'estimate':costs[opts['sketch_detail']],'count':100}
        with patch('AutoSketchBudget.time.monotonic',return_value=0):
            for seconds,expected in ((60,'Simple'),(90,'Balanced'),(120,'Detailed')):
                p=choose_sketch(None,(100,100),{'max_seconds':seconds},planner,Mock())
                self.assertEqual(p['options']['sketch_auto_meta']['selected_detail'],expected)
                self.assertLessEqual(p['estimate'],seconds*.85)
    def test_cancellation_and_invalid_time(self):
        with self.assertRaises(InterruptedError):choose_sketch(None,(1,1),{},Mock(),Mock(),lambda:True)
        for value in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):choose_sketch(None,(1,1),{'max_seconds':value},Mock(),Mock())
    def test_planning_time_is_subtracted(self):
        def planner(im,area,opts,cancelled):return {'options':dict(opts),'estimate':48,'count':10}
        with patch('AutoSketchBudget.time.monotonic',side_effect=[0,5,5,5,5,5,5,5,5,5]):
            with self.assertRaisesRegex(ValueError,'continuous paths'):
                choose_sketch(None,(1,1),{'max_seconds':60},planner,Mock())
    def test_auto_reduces_real_contours_and_preview(self):
        im=Image.new('RGB',(200,160),'white');d=ImageDraw.Draw(im)
        for x in range(10,190,20):
            for y in range(10,150,20):d.ellipse((x,y,x+12,y+12),fill='black')
        opts=dict(outline=True,paint_current_color=True,sketch_detail='Auto',profile_key='gartic-phone',
                  max_seconds=5,delay=.03,detail=8,brush_px=1,lines=True,contrast=1)
        with patch('AutoSketchBudget.time.monotonic',return_value=0):
            p=make_plan(im,im.size,opts)
        self.assertLessEqual(p['estimate'],4.25)
        self.assertGreater(p['count'],0)
        self.assertGreater(p['options']['sketch_auto_meta']['paths_omitted'],0)
        self.assertEqual(sum(map(len,p['execution_groups'])),p['count'])
        self.assertEqual(opts['sketch_detail'],'Auto')
    def test_manual_detail_does_not_enable_budget_reduction(self):
        p=make_plan(Image.new('RGB',(40,40),'white'),(40,40),dict(outline=True,paint_current_color=True,
            sketch_detail='Detailed',max_seconds=60,delay=.01,detail=8,brush_px=1,lines=True,contrast=1))
        self.assertNotIn('sketch_auto_meta',p['options'])
