import unittest
from collections import Counter
from types import SimpleNamespace

from LocalSanitization import safe_context
from DrawBot import DrawBotApp, execute_plan, finish_plan
from PIL import Image
from SpeedOptimizer import (SPEED_PROFILES, estimated_motion_seconds, normalize_speed,
                            optimize_strokes, phase_delay, travel_distance)


class Value:
    def __init__(self, value): self.value=value
    def get(self): return self.value


def undirected(stroke):
    x1,y1,x2,y2=stroke
    a,b=(x1,y1),(x2,y2)
    return (a,b) if a<=b else (b,a)


class SpeedOptimizerV105Tests(unittest.TestCase):
    def setUp(self):
        # Deliberately poor travel order: alternating far-left/far-right strokes.
        self.strokes=[]
        for i in range(80):
            x=10 if i%2==0 else 900
            y=(i*17)%500
            self.strokes.append((x,y,x+8,y+3))

    def test_profiles_are_explicit_and_legacy_names_migrate(self):
        self.assertEqual(tuple(SPEED_PROFILES),('Safe','Balanced','Fast'))
        self.assertEqual(normalize_speed('Careful'),'Safe')
        self.assertEqual(normalize_speed('Normal'),'Balanced')
        self.assertEqual(normalize_speed('Fast'),'Fast')
        with self.assertRaises(ValueError):normalize_speed('Unsafe turbo')

    def test_motion_waits_are_monotonic(self):
        for phase in ('path','travel','boundary'):
            safe=phase_delay(.01,'Safe',phase)
            balanced=phase_delay(.01,'Balanced',phase)
            fast=phase_delay(.01,'Fast',phase)
            self.assertGreater(safe,balanced)
            self.assertGreater(balanced,fast)

    def test_optimizer_preserves_exact_undirected_geometry(self):
        for speed in SPEED_PROFILES:
            out=optimize_strokes(self.strokes,speed)
            self.assertEqual(Counter(map(undirected,out)),Counter(map(undirected,self.strokes)))

    def test_optimizer_reduces_pen_up_travel(self):
        before=travel_distance(self.strokes)
        balanced=travel_distance(optimize_strokes(self.strokes,'Balanced'))
        fast=travel_distance(optimize_strokes(self.strokes,'Fast'))
        self.assertLess(balanced,before)
        self.assertLess(fast,before)
        self.assertLessEqual(fast,balanced)

    def test_priority_anchor_stays_first_in_each_window(self):
        out=optimize_strokes(self.strokes,'Balanced')
        window=SPEED_PROFILES['Balanced']['travel_window']
        for start in range(0,len(self.strokes),window):
            self.assertEqual(undirected(out[start]),undirected(self.strokes[start]))

    def test_eta_model_is_faster_for_faster_profiles(self):
        safe=estimated_motion_seconds(500,80,0,.01,'Safe')
        balanced=estimated_motion_seconds(500,80,0,.01,'Balanced')
        fast=estimated_motion_seconds(500,80,0,.01,'Fast')
        self.assertGreater(safe,balanced)
        self.assertGreater(balanced,fast)

    def test_finish_plan_eta_reflects_speed(self):
        image=Image.new('RGBA',(100,100),'white')
        groups=[self.strokes[:30]]
        common=dict(delay=.006,precision='High',paint_current_color=True,erase_mode=False,
                    brush_px=1,max_seconds=180,human_mode='Off')
        safe=finish_plan(image,(600,600),groups,dict(common,speed='Safe'))
        fast=finish_plan(image,(600,600),groups,dict(common,speed='Fast'))
        self.assertGreater(safe['estimate'],fast['estimate'])

    def test_options_migrates_normal_to_balanced(self):
        app=SimpleNamespace(
            brush_px=Value('2'),max_seconds=Value('180'),quality=Value('Balanced'),
            speed=Value('Normal'),precision=Value('High'),mode=Value('Lines (fastest)'),
            render_style=Value('Auto'),draw_quality=Value('High likeness'),human_mode=Value('Subtle'),
            game=Value('Other drawing app'),paint_tool=Value('Use current tool'),
            contrast=Value(1.0),portrait_focus=Value(True),skip_white=Value(True),outline=Value(False),
            paint_simple=Value(False))
        result=DrawBotApp.options(app)
        self.assertEqual(result['speed'],'Balanced')
        self.assertEqual(result['delay'],SPEED_PROFILES['Balanced']['base_delay'])

    def test_bug_report_context_allows_speed(self):
        cleaned=safe_context({'speed':'Fast','secret':'no'})
        self.assertEqual(cleaned['speed'],'Fast')
        self.assertNotIn('secret',cleaned)


class WaitRecorder:
    def __init__(self): self.seconds=[]
    def is_set(self): return False
    def wait(self,seconds): self.seconds.append(float(seconds)); return False


class FakeMouse:
    def __init__(self): self.held=False;self.position=(0,0)
    def move(self,x,y): self.position=(x,y)
    def press(self): self.held=True
    def release(self): self.held=False
    def click(self): pass


class SpeedExecutionTests(unittest.TestCase):
    def _run(self,speed):
        image=Image.new('RGBA',(100,100),'white')
        strokes=[(10,10,90,10),(90,20,10,20),(10,30,90,30)]
        options=dict(delay=SPEED_PROFILES[speed]['base_delay'],speed=speed,precision='High',
                     paint_current_color=True,erase_mode=False,brush_px=1,max_seconds=180,
                     human_mode='Off',tool_actions=[])
        plan=finish_plan(image,(400,400),[strokes],options)
        waits=WaitRecorder();mouse=FakeMouse()
        execute_plan(plan,(0,0,400,400),(),mouse,waits,__import__('threading').Event(),lambda *a:None,clock=lambda:0.0)
        return sum(waits.seconds)

    def test_fast_execution_wait_budget_is_lower_than_safe(self):
        self.assertLess(self._run('Fast'),self._run('Safe'))


if __name__=='__main__':unittest.main()
