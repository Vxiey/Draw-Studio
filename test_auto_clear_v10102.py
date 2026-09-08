import unittest,threading,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from PIL import Image,ImageDraw
from AutoDrawing import resolve_drawing
from DrawBot import DrawBotApp,make_plan,make_test_plan,execute_plan,_ensure_time_budget_options
from TimeBudget import resolve_time_budget_seconds
from test_drawbot import Mouse,NoWait,options

class AutoClearTests(unittest.TestCase):
    def test_auto_selects_from_image_and_keeps_manual(self):
        line=Image.new('RGB',(60,60),'white');ImageDraw.Draw(line).rectangle((20,20,40,40),fill='black')
        photo=Image.fromarray(np.random.default_rng(1).integers(0,256,(60,60,3),dtype=np.uint8))
        flat=Image.new('RGB',(60,60),'red')
        for im,engine in ((line,'black contours'),(flat,'Shape paths'),(photo,'Smart color paths')):
            self.assertEqual(resolve_drawing(im,{'render_preset':'Auto'})['auto_drawing_meta']['engine'],engine)
        self.assertEqual(resolve_drawing(line,{'render_preset':'Manual'}),{'render_preset':'Manual'})
    def test_masterpiece_is_unlimited_and_preserves_colour_resolution(self):
        o=resolve_drawing(Image.new('RGB',(30,20),'red'),{'render_preset':'Masterpiece','max_seconds':60,'gartic_timer_deadline':20})
        self.assertEqual(o['draw_quality'],'Pixel Accurate');self.assertTrue(o['unlimited_time'])
        self.assertNotIn('gartic_timer_deadline',o)
        plan=make_plan(Image.new('RGB',(30,20),'red'),(40,30),dict(options(),render_preset='Masterpiece',gpu_mode='CPU'))
        self.assertTrue(plan['options']['unlimited_time'])
        self.assertEqual(plan['image'].size,(40,27)) # aspect fitted
    def test_unlimited_does_not_send_expired_deadline_to_executor(self):
        o=_ensure_time_budget_options(dict(options(),unlimited_time=True,gartic_timer_deadline=0))
        self.assertNotIn('gartic_timer_deadline',o)
        self.assertEqual(resolve_time_budget_seconds('Unlimited',60),(3600,False))
        plan=make_test_plan((80,60),dict(o,paint_current_color=True))
        m=Mouse();execute_plan(plan,(100,100,80,60),(),m,NoWait(),threading.Event(),lambda *args:None)
        self.assertTrue(any(a[0]=='press' for a in m.actions));self.assertFalse(m.held)
    def app(self,remove):
        return SimpleNamespace(closing=False,pending_clear_drawing=remove,_clear_worker=None,activity=None,
          original=Image.new('RGB',(10,10)),plan={'old':True},pending_render_resume={'old':True},
          needs_plan=True,upscale_original=None,small_test_passed=True,color_session_cache={'old':1},
          file_label=Mock(),url=Mock(),progress={},set_busy=Mock(),summary=Mock(),status=Mock(),
          show_previews=Mock(),_sync_mobile_preview=Mock(),root=Mock())
    def test_clear_image_and_cache_clear_only_intended_memory(self):
        for remove in (False,True):
            a=self.app(remove);original=a.original
            with tempfile.TemporaryDirectory() as folder:
                files={k:Path(folder)/k for k in ('STATE_FILE','RENDER_FILE','IMAGE_FILE')}
                for f in files.values():f.write_text('old')
                with patch.multiple('SessionRecovery',**files):
                    DrawBotApp._finish_clear_drawing(a)
                self.assertTrue(all(not f.exists() for f in files.values()))
            self.assertIs(a.original,None if remove else original)
            self.assertIsNone(a.plan);self.assertIsNone(a.pending_render_resume)
    def test_late_worker_result_cannot_restore_cleared_image(self):
        a=self.app(True);old=a.original
        DrawBotApp._handle_event(a,'loaded',(Image.new('RGB',(2,2)),'late',''))
        DrawBotApp._handle_event(a,'planned',{'preview':'late'})
        self.assertIs(a.original,old)
        self.assertEqual(a.plan,{'old':True})
    def test_clear_waits_for_worker_before_deleting_cache(self):
        a=self.app(True);a._clear_worker=Mock();a._clear_worker.is_alive.return_value=True
        DrawBotApp._finish_clear_drawing(a)
        a.root.after.assert_called_once();self.assertIsNotNone(a.plan)

    def test_unlimited_survives_gartic_turbo_policy(self):
        from ProfileEngine import resolve_profile_policy
        effective,meta=resolve_profile_policy('Gartic Phone',{'time_budget_mode':'Unlimited','draw_quality':'High likeness'},mode='Auto')
        self.assertEqual(effective['time_budget_mode'],'Unlimited')
