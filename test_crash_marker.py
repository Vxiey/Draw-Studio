import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import CrashDiagnostics as cd


class CrashMarkerTests(unittest.TestCase):
    def test_marker_is_claimed_after_lock_and_owned_by_current_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'running.marker'
            with patch.object(cd,'RUN_MARKER',marker), patch.object(cd,'LOG_DIR',Path(tmp)):
                cd.RUN_MARKER_OWNED=False;cd.PREVIOUS_RUN_UNCLEAN=False
                cd.begin_run_marker()
                self.assertTrue(cd.RUN_MARKER_OWNED)
                self.assertIn('pid=',marker.read_text())
                cd.clean_exit()
                self.assertFalse(marker.exists())

    def test_existing_marker_is_detected_but_replaced_by_current_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'running.marker';marker.write_text('pid=123 started=old\n')
            with patch.object(cd,'RUN_MARKER',marker), patch.object(cd,'LOG_DIR',Path(tmp)):
                cd.RUN_MARKER_OWNED=False;cd.PREVIOUS_RUN_UNCLEAN=False
                cd.begin_run_marker()
                self.assertTrue(cd.PREVIOUS_RUN_UNCLEAN)
                self.assertNotEqual(marker.read_text().split()[0], 'pid=123')
                cd.clean_exit()

    def test_clean_exit_does_not_delete_unowned_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'running.marker';marker.write_text('pid=999 started=other\n')
            with patch.object(cd,'RUN_MARKER',marker), patch.object(cd,'LOG_DIR',Path(tmp)):
                cd.RUN_MARKER_OWNED=False
                cd.clean_exit()
                self.assertTrue(marker.exists())


if __name__=='__main__':unittest.main()
