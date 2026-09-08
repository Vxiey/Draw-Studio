import unittest
from types import SimpleNamespace
from DrawBot import DrawBotApp


class FakeRoot:
    def __init__(self):
        self.jobs=[]
        self.cancelled=[]
    def after(self,delay,callback):
        token=f'job-{len(self.jobs)+1}'
        self.jobs.append((token,delay,callback))
        return token
    def after_cancel(self,token):
        self.cancelled.append(token)


class PreviewSafetyTests(unittest.TestCase):
    def test_resize_render_is_debounced(self):
        root=FakeRoot()
        app=SimpleNamespace(root=root,closing=False,preview_render_after=None)
        app._run_scheduled_previews=lambda:DrawBotApp._run_scheduled_previews(app)
        DrawBotApp.schedule_previews(app)
        first=app.preview_render_after
        DrawBotApp.schedule_previews(app)
        self.assertEqual(root.cancelled,[first])
        self.assertNotEqual(app.preview_render_after,first)
        self.assertEqual(root.jobs[-1][1],45)

    def test_scheduled_callback_clears_token_before_render(self):
        calls=[]
        app=SimpleNamespace(closing=False,preview_render_after='job',show_previews=lambda:calls.append('render'))
        DrawBotApp._run_scheduled_previews(app)
        self.assertIsNone(app.preview_render_after)
        self.assertEqual(calls,['render'])

    def test_scheduled_callback_does_not_render_during_close(self):
        calls=[]
        app=SimpleNamespace(closing=True,preview_render_after='job',show_previews=lambda:calls.append('render'))
        DrawBotApp._run_scheduled_previews(app)
        self.assertIsNone(app.preview_render_after)
        self.assertEqual(calls,[])

    def test_preview_render_blocks_reentry(self):
        class Canvas:
            def __init__(self,owner,reenter=False):
                self.owner=owner;self.reenter=reenter;self.ovals=0
            def winfo_exists(self):return True
            def winfo_ismapped(self):return True
            def delete(self,*args):pass
            def winfo_width(self):return 400
            def winfo_height(self):return 240
            def create_oval(self,*args,**kwargs):
                self.ovals+=1
                if self.reenter:
                    self.reenter=False
                    DrawBotApp.show_previews(self.owner)
            def create_line(self,*args,**kwargs):pass
            def create_text(self,*args,**kwargs):pass
            def create_image(self,*args,**kwargs):pass
        app=SimpleNamespace(closing=False,preview_rendering=False,original=None,plan=None,photos=[])
        app.original_canvas=Canvas(app,True);app.result_canvas=Canvas(app)
        DrawBotApp.show_previews(app)
        self.assertFalse(app.preview_rendering)
        self.assertEqual(app.original_canvas.ovals,1)
        self.assertEqual(app.result_canvas.ovals,1)

    def test_recursion_callback_handler_is_bounded(self):
        messages=[]
        callbacks=[]
        class Status:
            def set(self,value):messages.append(value)
        class Root:
            def after(self,delay,callback):
                callbacks.append((delay,callback));return 'job'
        app=SimpleNamespace(status=Status(),root=Root(),closing=False)
        DrawBotApp.report_tk_callback_exception(app,RecursionError,RecursionError('boom'),None)
        self.assertEqual(messages,[])
        self.assertEqual(callbacks[0][0],25)
        callbacks[0][1]()
        self.assertIn('UI error contained',messages[-1])


if __name__=='__main__':unittest.main()
