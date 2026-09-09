import unittest
from collections import Counter
from PIL import Image

from ContinuousPaths import SMART_PATH_MODE, build_execution_paths, stats
from DrawBot import finish_plan
from ExtraFast2 import build_fast_paths
from StrokeOptimizer import optimize_execution_groups
from TimeBudget import apply_target_path_cap


def segments(paths):
    out=[]
    for path in paths:
        for a,b in zip(path,path[1:]):
            a=tuple(a);b=tuple(b)
            out.append((a,b) if a<=b else (b,a))
    return Counter(out)


class SemanticBarriersV10139Tests(unittest.TestCase):
    def _portrait_execution(self):
        groups=[[(0,0,2,1),(0,2,2,3),(0,10,100,10),(0,11,90,11)]]
        execution=build_execution_paths(groups,enabled=True,portrait_edge_count=2)
        return groups,execution

    def test_continuous_paths_exposes_portrait_semantics(self):
        groups,execution=self._portrait_execution()
        self.assertEqual(execution.protected_prefix_counts,[2])
        self.assertEqual(execution.phase_hints[0][:2],['portrait-outline','portrait-outline'])
        self.assertTrue(all(h=='portrait-tone' for h in execution.phase_hints[0][2:]))
        meta=stats(groups,execution)
        self.assertTrue(meta['portrait_semantic_barrier'])
        self.assertEqual(meta['protected_prefix_counts'],[2])
        self.assertEqual(meta['path_phase_hints'],execution.phase_hints)

    def test_target_cap_protects_portrait_prefix_before_longer_details(self):
        _groups,execution=self._portrait_execution()
        capped,meta=apply_target_path_cap(execution,2)
        self.assertEqual(len(capped[0]),2)
        self.assertEqual(capped.protected_prefix_counts,[2])
        self.assertEqual(capped.phase_hints,[['portrait-outline','portrait-outline']])
        self.assertEqual(meta['protected_prefix_before'],2)
        self.assertEqual(meta['protected_prefix_after'],2)
        self.assertFalse(meta['protected_prefix_truncated'])
        self.assertEqual(meta['path_phase_hints'],capped.phase_hints)

    def test_cap_smaller_than_prefix_stays_inside_prefix(self):
        raw=[[(0,0,1,0),(0,1,20,1),(0,2,5,2),(0,10,1000,10)]]
        execution=build_execution_paths(raw,enabled=True,portrait_edge_count=3)
        capped,meta=apply_target_path_cap(execution,2)
        source_edges={tuple(path) for path in execution[0][:3]}
        self.assertTrue(all(tuple(path) in source_edges for path in capped[0]))
        self.assertTrue(meta['protected_prefix_truncated'])
        self.assertEqual(meta['protected_prefix_after'],2)
        self.assertTrue(all(h=='portrait-outline' for h in capped.phase_hints[0]))

    def test_target_cap_filters_generic_phase_hints_exactly(self):
        paths=[[((0,0),(3,0)),((0,1),(100,1)),((0,2),(4,2)),((0,3),(90,3))]]
        hints=[['foundation','foundation','details','details']]
        capped,meta=apply_target_path_cap(paths,2,phase_hints=hints)
        self.assertEqual(capped[0],[paths[0][1],paths[0][3]])
        self.assertEqual(meta['path_phase_hints'],[['foundation','details']])
        self.assertTrue(meta['semantic_hints_preserved'])

    def test_optimizer_respects_filtered_execution_phase_hints(self):
        _groups,execution=self._portrait_execution()
        capped,_meta=apply_target_path_cap(execution,None)
        out,new_hints,opt_meta=optimize_execution_groups(
            capped,mode='Smart merge',drawing_mode=SMART_PATH_MODE,speed='Fast',phase_hints=capped.phase_hints)
        self.assertEqual(new_hints[0][:2],['portrait-outline','portrait-outline'])
        self.assertTrue(all(h=='portrait-tone' for h in new_hints[0][2:]))
        self.assertEqual(segments(out[0]),segments(capped[0]))
        self.assertEqual(opt_meta['stroke_optimizer_effective'],'Smart merge')

    def test_extra_fast_preserves_portrait_semantics_through_cap(self):
        groups=[[(0,0,2,1),(0,2,2,3)]+[(x,10,x,40) for x in range(4,30)]]
        execution,meta=build_fast_paths(
            groups,{'target_stroke_count_resolved':2,'stroke_optimizer':'Smart merge + 2-opt',
                    'drawing_mode':SMART_PATH_MODE,'speed':'Fast'},portrait_edge_count=2)
        self.assertEqual(execution.protected_prefix_counts,[2])
        self.assertEqual(execution.phase_hints[0][:2],['portrait-outline','portrait-outline'])
        capped,cap_meta=apply_target_path_cap(execution,2)
        self.assertEqual(capped.protected_prefix_counts,[2])
        self.assertEqual(capped.phase_hints,[['portrait-outline','portrait-outline']])
        self.assertEqual(cap_meta['protected_prefix_after'],2)
        self.assertTrue(meta['downstream_semantic_hints_preserved'])

    def test_finish_plan_keeps_portrait_outline_prefix_under_target_cap(self):
        edge_strokes=[(0,0,2,1),(0,2,2,3)]
        tone_strokes=[(0,10,100,10),(0,11,90,11)]
        groups=[edge_strokes+tone_strokes]
        opts={
            'drawing_mode':SMART_PATH_MODE,'lines':True,'smart_paths':True,
            'portrait_stats':{'edge_strokes':2},'target_stroke_count_resolved':2,
            'stroke_optimizer':'Smart merge','speed':'Balanced','brush_px':1,
            'paint_current_color':True,'skip_white':False,'delay':0.0,'human_mode':'Off',
            'color_order':[0],
        }
        plan=finish_plan(Image.new('RGBA',(120,30),'white'),(120,30),groups,opts)
        expected=[((0,0),(2,1)),((0,2),(2,3))]
        self.assertEqual(segments(plan['execution_groups'][0]),segments(expected))
        meta=plan['path_stats']
        self.assertTrue(meta['portrait_semantic_barrier'])
        self.assertEqual(meta['protected_prefix_before'],2)
        self.assertEqual(meta['protected_prefix_after'],2)
        self.assertEqual(meta['path_phase_hints'],[['portrait-outline','portrait-outline']])

    def test_finish_plan_keeps_outline_tone_optimizer_barrier_without_cap(self):
        groups=[[(0,0,2,1),(0,2,2,3),(0,10,100,10),(0,11,90,11)]]
        opts={
            'drawing_mode':SMART_PATH_MODE,'lines':True,'smart_paths':True,
            'portrait_stats':{'edge_strokes':2},'target_stroke_count_resolved':None,
            'stroke_optimizer':'Smart merge','speed':'Fast','brush_px':1,
            'paint_current_color':True,'skip_white':False,'delay':0.0,'human_mode':'Off',
            'color_order':[0],
        }
        plan=finish_plan(Image.new('RGBA',(120,30),'white'),(120,30),groups,opts)
        hints=plan['path_stats']['path_phase_hints'][0]
        self.assertEqual(hints[:2],['portrait-outline','portrait-outline'])
        self.assertTrue(all(h=='portrait-tone' for h in hints[2:]))
        self.assertTrue(plan['path_stats']['portrait_semantic_barrier'])


if __name__=='__main__':
    unittest.main()
