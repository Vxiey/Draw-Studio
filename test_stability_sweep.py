import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import CrashDiagnostics
from DrawBot import DrawBotApp, grab_area, load_image
from RuntimePaths import atomic_write_text


class Value:
    def __init__(self, value=None): self.value=value
    def get(self): return self.value
    def set(self, value): self.value=value


class StabilitySweepTests(unittest.TestCase):
    def test_atomic_write_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'settings.json'
            path.write_text('old',encoding='utf-8')
            atomic_write_text(path,json.dumps({'ok':True}))
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),{'ok':True})
            self.assertEqual(list(Path(tmp).glob('*.tmp')),[])


    def test_large_capture_is_rejected_before_screen_grab(self):
        with self.assertRaisesRegex(ValueError,'too large'):
            grab_area((0,0,10000,5000))

    def test_missing_local_image_has_bounded_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing=Path(tmp)/'missing.png'
            with self.assertRaisesRegex(ValueError,'no longer exists'):
                load_image(missing)

    def test_progress_zero_total_is_safe(self):
        app=SimpleNamespace(
            progress={'value':99},paused=threading.Event(),status=Value(''),
            root=None,closing=False,activity='draw'
        )
        DrawBotApp._handle_event(app,'progress',(0,0))
        self.assertEqual(app.progress['value'],0)

    def test_unknown_queue_event_is_ignored(self):
        app=SimpleNamespace()
        # Unknown internal queue messages should be logged, not crash the UI.
        DrawBotApp._handle_event(app,'future-event',{'x':1})

    def test_crash_log_rotation_keeps_one_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'session.log'
            path.write_bytes(b'x'*128)
            CrashDiagnostics._rotate_if_large(path,64)
            self.assertFalse(path.exists())
            self.assertEqual(path.with_suffix('.log.1').stat().st_size,128)

    def test_safe_after_cancel_tolerates_invalid_token(self):
        class Root:
            def after_cancel(self, token): raise RuntimeError('root already closed')
        app=SimpleNamespace(root=Root(),preview_after='dead-token')
        self.assertFalse(DrawBotApp._cancel_after_attr(app,'preview_after'))
        self.assertIsNone(app.preview_after)


if __name__=='__main__':
    unittest.main()
