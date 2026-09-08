import unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from ProfileIsolation import capture_defaults,reset_settings,scope_visible,extra_settings,restore_extra,SETTING_NAMES,register_controls,update_visibility

class Var:
    def __init__(self,v):self.v=v
    def get(self):return self.v
    def set(self,v):self.v=v

class ProfileIsolationTests(unittest.TestCase):
    def app(self):
        app=SimpleNamespace(**{name:Var('Auto') for name in SETTING_NAMES})
        for key,value in dict(quality='Balanced',speed='Balanced',precision='High',render_preset='Auto',outline=False,paint_simple=False,brush_px='3',max_seconds='180',contrast=1.,skip_white=True,subject_focus='Off',ui_mode='Simple',read_gartic_timer=True,portrait_focus=True).items():getattr(app,key).set(value)
        app.corners=[];app.saved_area=None;app.closing=False;app.profile_change_in_progress=False
        capture_defaults(app);return app

    def test_absent_profile_cannot_inherit_settings(self):
        app=self.app();app.render_preset.set('Masterpiece');app.max_seconds.set('3600');app.brush_px.set('22');app.outline.set(True)
        app.subject_region=(1,2,3,4);app._before_master_time='60 sec'
        reset_settings(app)
        self.assertEqual(app.render_preset.get(),'Auto');self.assertEqual(app.max_seconds.get(),'180')
        self.assertEqual(app.brush_px.get(),'3');self.assertFalse(app.outline.get());self.assertIsNone(app.subject_region)
        self.assertFalse(hasattr(app,'_before_master_time'))

    def test_real_save_load_round_trip_two_files(self):
        from DrawBot import DrawBotApp
        app=self.app()
        with tempfile.TemporaryDirectory() as temp:
            a,b=Path(temp)/'paint.json',Path(temp)/'gartic.json'
            app.settings_path=a;app.render_preset.set('Extra fast');app.brush_px.set('1');app.max_seconds.set('900');app.ui_mode.set('Advanced')
            DrawBotApp.save_settings(app)
            reset_settings(app);app.settings_path=b;DrawBotApp.read_settings(app)
            self.assertEqual(app.brush_px.get(),'3');self.assertEqual(app.render_preset.get(),'Auto')
            app.max_seconds.set('60');app.render_preset.set('Manual');DrawBotApp.save_settings(app)
            reset_settings(app);app.settings_path=a;DrawBotApp.read_settings(app)
            self.assertEqual(app.render_preset.get(),'Extra fast');self.assertEqual(app.max_seconds.get(),'900');self.assertEqual(app.ui_mode.get(),'Advanced')
            reset_settings(app);app.settings_path=b;DrawBotApp.read_settings(app)
            self.assertEqual(app.max_seconds.get(),'60');self.assertEqual(app.render_preset.get(),'Manual')

    def test_scope_matrix(self):
        self.assertTrue(scope_visible('paint','microsoft-paint'));self.assertFalse(scope_visible('paint','gartic-phone'))
        self.assertTrue(scope_visible('gartic','gartic-phone'));self.assertFalse(scope_visible('gartic','skribbl'))
        self.assertFalse(scope_visible('browser','microsoft-paint'));self.assertTrue(scope_visible('browser','gartic-phone'))
        self.assertFalse(scope_visible('nonpaint','microsoft-paint'))

    def test_visibility_switch_is_idempotent(self):
        parent=SimpleNamespace();children=[];parent.winfo_children=lambda:children
        class Widget:
            def __init__(self):self.master=parent;self.manager='pack';self.calls=0;children.append(self)
            def pack_info(self):return {'fill':'x'}
            def winfo_manager(self):return self.manager
            def pack(self,**kwargs):self.manager='pack';self.calls+=1
            def pack_forget(self):self.manager='';self.calls+=1
        paint,gartic=Widget(),Widget();app=SimpleNamespace()
        register_controls(app,[(paint,'paint'),(gartic,'gartic')])
        update_visibility(app,'microsoft-paint');self.assertEqual(gartic.manager,'')
        n=paint.calls+gartic.calls;update_visibility(app,'microsoft-paint');self.assertEqual(paint.calls+gartic.calls,n)
        update_visibility(app,'gartic-phone');self.assertEqual(paint.manager,'');self.assertEqual(gartic.manager,'pack')
