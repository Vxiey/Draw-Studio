import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import RuntimePaths


class RuntimePathTests(unittest.TestCase):
    def test_source_helper_uses_python_and_loose_script(self):
        with patch.object(RuntimePaths.sys, 'frozen', False, create=True):
            command = RuntimePaths.helper_command('mouse', '--diagnostics-only')
        self.assertEqual(command[0], RuntimePaths.sys.executable)
        self.assertTrue(command[1].endswith('MouseProbe.py'))
        self.assertIn('--diagnostics-only', command)

    def test_frozen_mouse_helper_relaunches_same_exe(self):
        with patch.object(RuntimePaths.sys, 'frozen', True, create=True), \
             patch.object(RuntimePaths.sys, 'executable', r'C:\\Apps\\ImageDrawBot.exe'):
            command = RuntimePaths.helper_command('mouse', '--handle', 123)
        self.assertEqual(command[:2], [r'C:\\Apps\\ImageDrawBot.exe', '--internal-mouse-probe'])
        self.assertEqual(command[-2:], ['--handle', '123'])

    def test_frozen_target_helper_relaunches_same_exe(self):
        with patch.object(RuntimePaths.sys, 'frozen', True, create=True), \
             patch.object(RuntimePaths.sys, 'executable', r'C:\\Apps\\ImageDrawBot.exe'):
            command = RuntimePaths.helper_command('target', '--area', 1, 2, 3, 4)
        self.assertEqual(command[1], '--internal-target-probe')
        self.assertEqual(command[-5:], ['--area', '1', '2', '3', '4'])

    def test_frozen_data_dir_uses_localappdata(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, {'LOCALAPPDATA': temp}), \
             patch.object(RuntimePaths.sys, 'frozen', True, create=True):
            path = RuntimePaths.data_dir()
        self.assertEqual(path, Path(temp) / 'ImageDrawBot')


if __name__ == '__main__':
    unittest.main()
