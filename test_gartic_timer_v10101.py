import unittest,threading
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from GarticTimer import find_timer,read_ring,estimate_remaining,observe_timer,apply_timer_budget
from DrawBot import _ensure_time_budget_options,execute_plan,make_test_plan
from test_drawbot import Mouse,NoWait,options

class TimerTests(unittest.TestCase):
    def frame(self,fraction=.5,size=80):
        im=Image.new('RGB',(320,240),(158,25,82));d=ImageDraw.Draw(im)
        cx,cy=240,70;r=size//2
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(199,160,175))
        q=r-5;d.ellipse((cx-q,cy-q,cx+q,cy+q),fill=(116,18,55))
        q=r-10
        if fraction>0:d.pieslice((cx-q,cy-q,cx+q,cy+q),-90,-90+360*fraction,fill='white')
        return im
    def test_fraction_at_different_sizes(self):
        for size in (70,80,100):
            for f in (.25,.5,.75):
                # Preserve relative ring geometry while scaling the reference.
                im=self.frame(f).resize((round(320*size/80),round(240*size/80)))
                self.assertAlmostEqual(find_timer(im)['fraction'],f,delta=.035)
    def test_single_frame_never_supplies_seconds(self):
        self.assertNotIn('estimated_seconds',find_timer(self.frame()))
        with self.assertRaises(ValueError):estimate_remaining([(0,.5)])
    def test_static_reset_and_missing_timer_rejected(self):
        for fs in ([.5]*7,[.5,.49,.48,.9,.89,.88,.87]):
            with self.assertRaises(ValueError):estimate_remaining(list(enumerate(fs)))
        with self.assertRaises(ValueError):find_timer(Image.new('RGB',(320,240),'white'))
    def test_seconds_from_motion_not_total_duration_assumption(self):
        for total in (60,120,240):
            obs=[(100+i,.5-i/total) for i in range(7)]
            r=estimate_remaining(obs)
            self.assertAlmostEqual(r['estimated_seconds'],total/2-6,places=6)
            self.assertLess(r['safe_seconds'],r['estimated_seconds'])
    def test_budget_survives_old_preset_and_subtracts_elapsed(self):
        r=estimate_remaining([(100+i,.5-i/120) for i in range(7)])
        o=apply_timer_budget({'max_seconds':180,'manual_max_seconds':180,'time_budget_mode':'60 sec','outline':True},r,clock=lambda:110)
        p=_ensure_time_budget_options(o)
        self.assertEqual(p['max_seconds'],int(r['deadline']-110))
        self.assertEqual(p['sketch_detail'],'Auto')
        self.assertEqual(p['gartic_timer_deadline'],r['deadline'])
    def test_observation_cancellable(self):
        stop=Mock();stop.is_set.return_value=True
        with self.assertRaises(InterruptedError):observe_timer(Mock(),None,stop)
    def test_sequence_on_synthetic_frames(self):
        frames=iter([self.frame(.5-i/120) for i in range(7)])
        stop=Mock();stop.is_set.return_value=False;stop.wait.return_value=False
        times=iter(range(100,107))
        result=observe_timer(lambda:next(frames),None,stop,clock=lambda:next(times))
        self.assertAlmostEqual(result['estimated_seconds'],54,delta=8)
    def test_expired_deadline_sends_no_press(self):
        plan=make_test_plan((80,60),dict(options(),paint_current_color=True,gartic_timer_deadline=0))
        mouse=Mouse()
        try:execute_plan(plan,(100,100,80,60),(),mouse,NoWait(),threading.Event(),lambda *a:None)
        except InterruptedError:pass
        self.assertFalse(any(a[0]=='press' for a in mouse.actions))
