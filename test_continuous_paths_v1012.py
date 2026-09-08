import threading
import unittest
from PIL import Image

from ContinuousPaths import SMART_PATH_MODE, build_execution_paths
from DrawBot import make_plan, execute_plan
from test_drawbot import Mouse, NoWait


def base_options(**updates):
    options=dict(detail=10,delay=.01,speed='Balanced',precision='High',lines=True,
                 drawing_mode=SMART_PATH_MODE,skip_white=True,contrast=1,outline=False,
                 human_mode='Off',brush_px=1,max_seconds=180)
    options.update(updates)
    return options


class ContinuousPathTests(unittest.TestCase):
    def test_full_block_becomes_one_continuous_path(self):
        plan=make_plan(Image.new('RGBA',(8,5),'black'),(80,50),base_options())
        self.assertGreater(plan['source_count'],plan['count'])
        self.assertEqual(plan['count'],1)
        self.assertEqual(plan['path_stats']['joined_strokes'],plan['source_count']-1)
        self.assertIsNotNone(plan['execution_groups'])

    def test_gap_is_never_bridged(self):
        groups=[[(0,0,4,0),(0,2,4,2)]]
        paths=build_execution_paths(groups,enabled=True)[0]
        self.assertEqual(len(paths),2)

    def test_connector_stays_on_planned_pixels(self):
        strokes=[(0,0,5,0),(2,1,7,1),(1,2,4,2),(9,2,10,2)]
        paths=build_execution_paths([strokes],enabled=True)[0]
        covered=set()
        for x1,y1,x2,_ in strokes:
            for x in range(min(x1,x2),max(x1,x2)+1):covered.add((x,y1))
        for path in paths:
            for (x1,y1),(x2,y2) in zip(path,path[1:]):
                if y1==y2:
                    for x in range(min(x1,x2),max(x1,x2)+1):
                        self.assertIn((x,y1),covered)
                else:
                    self.assertEqual(x1,x2)
                    self.assertEqual(abs(y2-y1),1)
                    self.assertIn((x1,y1),covered);self.assertIn((x2,y2),covered)

    def test_legacy_line_mode_is_unchanged(self):
        legacy=base_options(drawing_mode='Lines (fastest)')
        plan=make_plan(Image.new('RGBA',(8,5),'black'),(80,50),legacy)
        self.assertIsNone(plan['execution_groups'])
        self.assertEqual(plan['count'],sum(map(len,plan['groups'])))

    def test_execution_uses_single_mouse_down_for_joined_block(self):
        plan=make_plan(Image.new('RGBA',(8,5),'black'),(80,50),base_options())
        mouse=Mouse();events=[]
        execute_plan(plan,(100,100,80,50),[(5,i) for i in range(18)],mouse,NoWait(),threading.Event(),lambda *e:events.append(e))
        # v1.0.53 clips the joined path against the brush-inset safe canvas.
        # Edge connectors that would run outside the safe polygon are no longer
        # drawn, so one logical source path may execute as several safe subpaths.
        self.assertGreaterEqual(sum(a[0]=='press' for a in mouse.actions),1)
        for action in mouse.actions:
            if action[0]=='move' and action[1] >= 100 and action[2] >= 100:
                self.assertGreaterEqual(action[1],103); self.assertLessEqual(action[1],176)
                self.assertGreaterEqual(action[2],103); self.assertLessEqual(action[2],146)
        self.assertIn(('progress',(1,1)),events)
        self.assertFalse(mouse.held)

    def test_portrait_edges_are_not_joined_into_tonal_paths(self):
        groups=[[(0,0,3,1),(0,2,5,2),(0,3,5,3)]]
        paths=build_execution_paths(groups,enabled=True,portrait_edge_count=1)[0]
        self.assertEqual(paths[0],((0,0),(3,1)))
        self.assertEqual(len(paths),2)


if __name__=='__main__':unittest.main()
