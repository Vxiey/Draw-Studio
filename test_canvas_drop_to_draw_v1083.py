import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from DrawBot import DrawBotApp
from DropInStart import DROP_IN_ACTION


class Value:
    def __init__(self, value): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class TkStub:
    @staticmethod
    def splitlist(value):
        return (value,)


class CanvasDropToDrawV1083Tests(unittest.TestCase):
    def make_app(self, path):
        loaded = []
        app = SimpleNamespace(
            activity=None, closing=False,
            root=SimpleNamespace(tk=TkStub()),
            game=Value('Other drawing app'),
            manual_drop_in_start=Value(False), manual_drop_in_armed_until=0.0,
            browser_one_click_enabled=Value(False),
            status=Value(''),
        )
        app.load_source = lambda source, label, action=None: loaded.append((source, label, action)) or True
        return app, loaded

    def test_direct_canvas_drop_arms_one_shot_start_when_ready(self):
        with tempfile.NamedTemporaryFile(suffix='.png') as handle:
            app, loaded = self.make_app(handle.name)
            event = SimpleNamespace(data=handle.name)
            with mock.patch.object(DrawBotApp, '_manual_drop_in_armed', return_value=False), \
                 mock.patch.object(DrawBotApp, '_browser_one_click_active', return_value=False), \
                 mock.patch.object(DrawBotApp, 'arm_manual_drop_in', return_value=True):
                result = DrawBotApp.drop_image(app, event, drop_to_draw=True)
        self.assertEqual(result, 'copy')
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0][2], DROP_IN_ACTION)

    def test_window_drop_remains_import_only(self):
        with tempfile.NamedTemporaryFile(suffix='.png') as handle:
            app, loaded = self.make_app(handle.name)
            event = SimpleNamespace(data=handle.name)
            with mock.patch.object(DrawBotApp, '_manual_drop_in_armed', return_value=False):
                result = DrawBotApp.drop_image(app, event, drop_to_draw=False)
        self.assertEqual(result, 'copy')
        self.assertIsNone(loaded[0][2])


if __name__ == '__main__':
    unittest.main()
