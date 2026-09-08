import unittest
from types import SimpleNamespace
from DrawBot import DrawBotApp


class Value:
    def __init__(self,value): self.value=value
    def get(self): return self.value


class Root:
    def __init__(self):
        self.jobs=[];self.cancelled=[]
    def after_idle(self,callback):
        token=f'idle-{len(self.jobs)+1}'
        self.jobs.append((token,callback))
        return token
    def after_cancel(self,token): self.cancelled.append(token)


class Status:
    def __init__(self): self.values=[]
    def set(self,value): self.values.append(value)


class ProfileSwitchSafetyTests(unittest.TestCase):
    def test_profile_change_is_deferred_out_of_optionmenu_callback(self):
        root=Root();saved=[]
        app=SimpleNamespace(
            root=root,activity=None,closing=False,game=Value('Microsoft Paint'),
            profile_change_after=None,status=Status(),save_settings=lambda:saved.append(True),
        )
        app._apply_profile_change=lambda selected:None
        DrawBotApp.change_profile(app)
        self.assertEqual(saved,[True])
        self.assertEqual(len(root.jobs),1)
        self.assertEqual(app.profile_change_after,'idle-1')

    def test_profile_change_entrypoint_contains_no_mouse_or_window_activation(self):
        import inspect
        source=inspect.getsource(DrawBotApp.change_profile)+inspect.getsource(DrawBotApp._apply_profile_change)
        for forbidden in ('SetCursorPos','SendInput','mouse.move','mouse.press','prepare_target','SetForegroundWindow'):
            self.assertNotIn(forbidden,source)

    def test_repeated_profile_change_coalesces_previous_idle_job(self):
        root=Root()
        app=SimpleNamespace(
            root=root,activity=None,closing=False,game=Value('Microsoft Paint'),
            profile_change_after=None,status=Status(),save_settings=lambda:None,
        )
        app._apply_profile_change=lambda selected:None
        DrawBotApp.change_profile(app)
        first=app.profile_change_after
        DrawBotApp.change_profile(app)
        self.assertEqual(root.cancelled,[first])
        self.assertNotEqual(app.profile_change_after,first)


if __name__=='__main__': unittest.main()
