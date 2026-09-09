import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image

from StabilityRC import migrate_settings,safe_release_and_disarm,current_completion,run_start_stop_model,SETTINGS_SCHEMA
from DropInSynchronization import make_request,target_matches
from BrowserAutoRecalibration import make_layout_state,compare_layout_states
from LayoutFingerprintV2 import load_cache

class Mouse:
    def __init__(self,release_error=False,disarm_error=False):self.released=0;self.disarmed=0;self.release_error=release_error;self.disarm_error=disarm_error
    def release(self):
        self.released+=1
        if self.release_error:raise OSError('release fail')
    def disarm_input(self):
        self.disarmed+=1
        if self.disarm_error:raise OSError('disarm fail')

class StabilityRCTests(unittest.TestCase):
    def test_150_start_stop_cycles_finish_disarmed(self):
        result=run_start_stop_model(150);self.assertEqual(result['cycles'],150);self.assertIsNone(result['activity']);self.assertFalse(result['armed']);self.assertFalse(result['pending'])
    def test_mouse_disarms_even_if_release_throws(self):
        m=Mouse(release_error=True);errors=safe_release_and_disarm(m);self.assertEqual(m.released,1);self.assertEqual(m.disarmed,1);self.assertEqual(errors[0][0],'release')
    def test_mouse_cleanup_contains_both_failures(self):
        m=Mouse(True,True);self.assertEqual(len(safe_release_and_disarm(m)),2)
    def test_dry_run_never_calls_release_but_disarms(self):
        m=Mouse();safe_release_and_disarm(m,dry_run=True);self.assertEqual(m.released,0);self.assertEqual(m.disarmed,1)
    def test_stale_worker_completion_cannot_clear_new_activity(self):
        self.assertFalse(current_completion('draw','load'));self.assertTrue(current_completion('draw','draw'))
    def test_settings_migration_removes_old_auto_authorization(self):
        out=migrate_settings({'brush_width':'7','max_time':90,'auto_draw':True,'full_draw_armed':True});self.assertEqual(out['brush_px'],'7');self.assertEqual(out['max_seconds'],90);self.assertNotIn('auto_draw',out);self.assertEqual(out['settings_schema'],SETTINGS_SCHEMA)
    def test_drop_in_latest_wins_for_200_replacements(self):
        fp=('Gartic Phone',123,(0,0,100,100),(0,0,90,90),96);req=None
        for i in range(200):req=make_request(i,f'image-{i}','Draw immediately (armed)',fp,previous=req,now=10+i*.001,timeout_seconds=30)
        self.assertEqual(req.sequence,200);self.assertEqual(req.source,199);self.assertTrue(target_matches(req,fp))
    def test_repeated_zoom_resize_detected(self):
        base=make_layout_state((0,0,1200,800),96,(100,100,1000,650),[(120,700),(160,700),(200,700)])
        old=base
        changes=0
        for i in range(120):
            d=i%9
            new=make_layout_state((0,0,1200+d,800+(d//2)),96+(24 if i%17==0 else 0),(100,100,1000+d,650),[(120+d,700),(160+d,700),(200+d,700)])
            delta=compare_layout_states(old,new,tolerance_px=4);changes+=int(delta.changed);old=new
        self.assertGreater(changes,20)
    def test_browser_refresh_invalidates_visual_layout_state(self):
        old=make_layout_state((0,0,1200,800),96,(100,100,1000,650),[(120,700),(160,700),(200,700)])
        refreshed=make_layout_state((0,0,1200,800),96,None,[])
        delta=compare_layout_states(old,refreshed,tolerance_px=4)
        self.assertTrue(delta.changed);self.assertIn('canvas detection changed',delta.reasons)

    def test_window_switch_changes_drop_in_target_identity(self):
        fp=('Gartic Phone',123,(0,0,100,100),(0,0,90,90),96)
        req=make_request('x','image','Draw immediately (armed)',fp,now=1,timeout_seconds=30)
        switched=('Gartic Phone',456,(0,0,100,100),(0,0,90,90),96)
        self.assertFalse(target_matches(req,switched))

    def test_old_cache_version_fails_closed_without_crash(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'cache.json';p.write_text('{"version":1,"entries":[{"bad":true}]}',encoding='utf-8')
            result=load_cache(p);self.assertEqual(result['version'],3);self.assertEqual(result['entries'],[])

if __name__=='__main__':unittest.main()
