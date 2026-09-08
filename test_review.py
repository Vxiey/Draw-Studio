import json
import tempfile
import unittest
import threading
from pathlib import Path
from types import SimpleNamespace
from DrawBot import DrawBotApp

class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

def app_at(path):
    app=SimpleNamespace(settings_path=path,corners=[],saved_area=None,status=Value(''))
    for key,value in dict(quality='Balanserad',speed='Normal',mode='Linjer (snabbast)',skip_white=True,contrast=1,outline=False,brush_px='3',max_seconds='180',paint_simple=False,paint_tool='Use current tool').items():setattr(app,key,Value(value))
    return app

class ReviewTests(unittest.TestCase):
    def test_settings_roundtrip_brush_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'settings.json';app=app_at(path)
            app.brush_px.set('7');app.max_seconds.set('420');app.paint_tool.set('Eraser');DrawBotApp.save_settings(app)
            restored=app_at(path);DrawBotApp.read_settings(restored)
            self.assertEqual(restored.brush_px.get(),'7');self.assertEqual(restored.max_seconds.get(),'420');self.assertEqual(restored.paint_tool.get(),'Eraser')
    def test_invalid_settings_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'settings.json'
            for values in [{'brush_px':True,'max_seconds':'bad'},{'brush_px':'900','max_seconds':-1}]:
                path.write_text(json.dumps(values));app=app_at(path);DrawBotApp.read_settings(app)
                self.assertEqual(app.brush_px.get(),'3');self.assertEqual(app.max_seconds.get(),'180')
    def test_stop_cancels_pending_preview(self):
        cancelled=[]
        app=SimpleNamespace(drop_action_pending='Draw immediately',needs_plan=True,preview_after='preview-job',root=SimpleNamespace(after_cancel=cancelled.append),stop=threading.Event(),paused=threading.Event(),capture_job=None,status=Value(''),activity=None)
        DrawBotApp.cancel(app)
        self.assertEqual(cancelled,['preview-job']);self.assertIsNone(app.preview_after)
        self.assertFalse(app.needs_plan);self.assertIsNone(app.drop_action_pending);self.assertTrue(app.stop.is_set())

if __name__=='__main__':unittest.main()
