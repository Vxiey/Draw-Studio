import threading
import unittest
from PIL import Image, ImageDraw

from DrawBot import execute_plan
from VisualVerification import (compare_batch_snapshot, planned_batch_boxes,
                                planned_batch_points, resolve_visual_verification)
from test_drawbot import Mouse, NoWait


class SnapshotMouse(Mouse):
    def __init__(self, snapshots):
        super().__init__()
        self.snapshots=list(snapshots)
        self.snapshot_calls=0
    def snapshot_canvas(self, area):
        self.snapshot_calls+=1
        if self.snapshots:
            return self.snapshots.pop(0)
        return Image.new('RGB',(area[2],area[3]),'white')


def simple_visual_plan():
    opts={
        'delay':0.0,'speed':'Fast','precision':'Normal','human_mode':'Off','paint_current_color':False,
        'strict_color_verification':False,'adaptive_color_verification':False,'brush_px':2,
        'color_order':[0,1], 'render_resume_state':None,
        'visual_verification':'Balanced','visual_verification_resolved':'Balanced','visual_verification_enabled':True,
    }
    return {
        'options':opts,
        'image':Image.new('RGB',(2,2),'white'),
        'fitted':(20,20),
        'groups':[[(0,0,1,0)],[(0,1,1,1)]],
        'execution_groups':None,
        'execution_sequence':[],
        'count':2,
        'colors':((220,0,0),(0,180,0)),
        'color_selectors':(
            {'kind':'palette','palette_index':0,'rgb':(220,0,0)},
            {'kind':'palette','palette_index':1,'rgb':(0,180,0)},
        ),
        'path_stats':{},
    }


class VisualVerificationV1043Tests(unittest.TestCase):
    def test_resolve_auto_is_balanced_for_paint_and_off_for_generic(self):
        self.assertEqual(resolve_visual_verification('Auto',paint_profile=True),'Balanced')
        self.assertEqual(resolve_visual_verification('Auto',paint_profile=False),'Off')

    def test_batch_snapshot_detects_wrong_or_missing_color(self):
        after=Image.new('RGB',(40,20),'white')
        points=[(10,10),(20,10),(30,10)]
        result=compare_batch_snapshot(after,None,(0,0,40,20),(220,0,0),points,[(4,4,36,16)],brush_px=2,mode='Balanced')
        self.assertFalse(result['ok'])
        self.assertIn('missed-region-or-wrong-color',result['issues'])

    def test_batch_snapshot_detects_outside_fill_leak(self):
        before=Image.new('RGB',(80,60),'white')
        after=before.copy();d=ImageDraw.Draw(after)
        d.rectangle((0,0,79,59),fill=(220,0,0))
        d.line((10,10,25,10),fill=(220,0,0),width=3)
        result=compare_batch_snapshot(after,before,(0,0,80,60),(220,0,0),[(10,10),(20,10)],[(6,6,30,14)],brush_px=2,mode='Balanced')
        self.assertFalse(result['ok'])
        self.assertIn('outside-change-possible-fill-leak-or-wrong-place',result['issues'])

    def test_execute_verifies_after_each_finished_color_batch(self):
        plan=simple_visual_plan();area=(100,100,20,20)
        base=Image.new('RGB',(20,20),'white')
        first=base.copy();ImageDraw.Draw(first).line((5,5,15,5),fill=(220,0,0),width=4)
        second=first.copy();ImageDraw.Draw(second).line((5,15,15,15),fill=(0,180,0),width=4)
        mouse=SnapshotMouse([base,first,second]);events=[]
        execute_plan(plan,area,[(10,10),(20,10)],mouse,NoWait(),threading.Event(),lambda *e:events.append(e))
        visual=[v for k,v in events if k=='visual_verification' and isinstance(v,dict)]
        self.assertGreaterEqual(len(visual),3)  # baseline + two finished batches
        self.assertTrue(all(v.get('ok') for v in visual[1:]))
        self.assertEqual(mouse.snapshot_calls,3)

    def test_execute_stops_when_visual_diff_leaks_outside_batch(self):
        plan=simple_visual_plan();area=(100,100,20,20)
        base=Image.new('RGB',(20,20),'white')
        leaked=Image.new('RGB',(20,20),(220,0,0))
        mouse=SnapshotMouse([base,leaked]);events=[]
        with self.assertRaisesRegex(InterruptedError,'Visual verification stopped'):
            execute_plan(plan,area,[(10,10),(20,10)],mouse,NoWait(),threading.Event(),lambda *e:events.append(e))
        self.assertTrue(any(k=='visual_verification' and not v.get('ok') for k,v in events if isinstance(v,dict)))

if __name__=='__main__':
    unittest.main()
