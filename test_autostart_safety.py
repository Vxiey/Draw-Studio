import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from DrawBot import DrawBotApp


class Value:
    def __init__(self,value=None):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


class AutoStartSafetyTests(unittest.TestCase):
    def test_draw_rejects_internal_non_user_call(self):
        app=SimpleNamespace(status=Value())
        with patch('DrawBot.log_event') as log, patch('DrawBot.load_calibration') as calibration:
            DrawBotApp.draw(app)
        calibration.assert_not_called()
        self.assertIn('Unlock full drawing',app.status.get())
        self.assertTrue(log.called)

    def test_old_direct_drop_setting_migrates_to_show_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'settings.json'
            path.write_text(json.dumps({'drop_mode':'Draw immediately'}),encoding='utf-8')
            app=SimpleNamespace(
                settings_path=path,corners=[],saved_area=None,
                quality=Value('Balanced'),speed=Value('Normal'),mode=Value('Lines (fastest)'),
                skip_white=Value(True),outline=Value(False),contrast=Value(1.0),
                brush_px=Value('3'),max_seconds=Value('180'),paint_simple=Value(False),
                drop_mode=Value('Draw immediately'))
            DrawBotApp.read_settings(app)
            self.assertEqual(app.drop_mode.get(),'Show image')


if __name__=='__main__':unittest.main()
