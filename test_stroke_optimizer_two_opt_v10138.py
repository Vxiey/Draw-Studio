import random
import unittest
from collections import Counter

from AutoDrawing import resolve_drawing
from StrokeOptimizer import (
    _bounded_two_opt,
    _two_opt_budget,
    optimize_execution_groups,
    optimize_path_group,
    pen_up_distance,
)


def segment_multiset(paths):
    out=[]
    for path in paths:
        for a,b in zip(path,path[1:]):
            a=tuple(a);b=tuple(b)
            out.append((a,b) if a<=b else (b,a))
    return Counter(out)


class StrokeOptimizerTwoOptV10138Tests(unittest.TestCase):
    def test_two_opt_preserves_exact_segment_geometry(self):
        paths=[]
        for i in range(96):
            x=0 if i%2==0 else 900
            y=i*4
            paths.append(((x,y),(x+7,y)))
        before=segment_multiset(paths)
        out,meta=optimize_path_group(paths,mode='Smart merge + 2-opt',drawing_mode='Smart paths (recommended)',speed='Fast')
        self.assertEqual(segment_multiset(out),before)
        self.assertLessEqual(pen_up_distance(out),pen_up_distance(paths)+1e-9)
        self.assertEqual(meta['stroke_optimizer_effective'],'Smart merge + 2-opt')
        self.assertGreater(meta['optimizer_two_opt_evaluations'],0)

    def test_two_opt_never_regresses_smart_merge_travel(self):
        rng=random.Random(138)
        for _ in range(40):
            paths=[]
            for i in range(70):
                x=rng.randrange(-300,301)
                y=rng.randrange(-300,301)
                dx=rng.randrange(-12,13)
                dy=rng.randrange(-12,13)
                if dx==0 and dy==0:
                    dx=1
                paths.append(((x,y),(x+dx,y+dy)))
            baseline,_=optimize_path_group(paths,mode='Smart merge',drawing_mode='Shape paths',speed='Fast')
            refined,meta=optimize_path_group(paths,mode='Smart merge + 2-opt',drawing_mode='Shape paths',speed='Fast')
            self.assertEqual(segment_multiset(refined),segment_multiset(baseline))
            self.assertLessEqual(pen_up_distance(refined),pen_up_distance(baseline)+1e-9)
            self.assertLessEqual(meta['optimizer_two_opt_after'],meta['optimizer_two_opt_before']+1e-9)

    def test_phase_barriers_remain_contiguous_and_geometry_exact(self):
        foundation=[((0,i*8),(5,i*8)) for i in range(24)]
        details=[((1000,i*8),(1005,i*8)) for i in range(24)]
        group=[];hints=[]
        for a,b in zip(foundation,details):
            group.extend((a,b));hints.extend(('foundation','details'))
        source=segment_multiset(group)
        out,new_hints,meta=optimize_execution_groups(
            [group],mode='Smart merge + 2-opt',drawing_mode='Shape paths',speed='Fast',phase_hints=[hints])
        self.assertEqual(segment_multiset(out[0]),source)
        self.assertEqual(len(new_hints[0]),len(out[0]))
        transitions=sum(1 for a,b in zip(new_hints[0],new_hints[0][1:]) if a!=b)
        self.assertGreater(transitions,1)
        # Every input phase block is optimized independently; the alternating
        # semantic sequence must therefore remain alternating rather than being
        # globally clustered by travel distance.
        self.assertEqual(new_hints[0],hints)
        self.assertEqual(meta['stroke_optimizer_effective'],'Smart merge + 2-opt')

    def test_two_opt_cancellation_is_checked_inside_local_search(self):
        paths=[((i*10,0),(i*10+3,0)) for i in range(100)]
        calls={'n':0}
        def cancelled():
            calls['n']+=1
            return calls['n']>6
        with self.assertRaises(InterruptedError):
            _bounded_two_opt(paths,speed='Fast',cancelled=cancelled)
        self.assertGreater(calls['n'],6)

    def test_large_path_budget_is_bounded_and_ordered_input_stops_early(self):
        n=13000
        passes,window=_two_opt_budget('Fast',n)
        self.assertLessEqual(passes,6)
        self.assertLessEqual(window,12)
        paths=[((i*4,0),(i*4+1,0)) for i in range(n)]
        out,meta=_bounded_two_opt(paths,speed='Fast')
        self.assertEqual(len(out),n)
        self.assertEqual(segment_multiset(out),segment_multiset(paths))
        self.assertLessEqual(meta['optimizer_two_opt_after'],meta['optimizer_two_opt_before']+1e-9)
        self.assertEqual(meta['optimizer_two_opt_iterations'],1)
        self.assertLessEqual(meta['optimizer_two_opt_evaluations'],n*window)

    def test_allow_reverse_false_disables_two_opt(self):
        paths=[((100,0),(110,0)),((0,0),(10,0)),((50,0),(60,0)),((20,0),(30,0))]
        out,meta=_bounded_two_opt(paths,speed='Fast',allow_reverse=False)
        self.assertEqual(out,paths)
        self.assertEqual(meta['optimizer_two_opt_evaluations'],0)
        self.assertEqual(meta['optimizer_two_opt_improvements'],0)

    def test_extra_fast_preset_enables_internal_two_opt_mode(self):
        class ImageStub:
            pass
        out=resolve_drawing(ImageStub(),{'render_preset':'Extra fast','fill_tool_available':False})
        self.assertEqual(out['stroke_optimizer'],'Smart merge + 2-opt')
        self.assertTrue(out['extra_fast'])
        self.assertTrue(out['extra_fast_v2'])


if __name__=='__main__':
    unittest.main()
