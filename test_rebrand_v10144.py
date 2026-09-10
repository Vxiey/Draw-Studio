import unittest
from pathlib import Path
from unittest import mock

from Version import APP_NAME, APP_TAGLINE, APP_VERSION, FILE_VERSION
import UpdateCenter

ROOT=Path(__file__).resolve().parent

class RebrandV10144Tests(unittest.TestCase):
    def test_public_identity(self):
        self.assertEqual(APP_NAME,'Image Draw Bot')
        self.assertEqual(APP_TAGLINE,'Automatic Image Drawing')
        self.assertEqual(APP_VERSION,'1.0.144-rc1')
        self.assertEqual(FILE_VERSION,'1.0.144')
        self.assertEqual(UpdateCenter.GITHUB_REPOSITORY,'Vxiey/Image-Draw-Bot')

    def test_windows_identity(self):
        installer=(ROOT/'installer'/'ImageDrawBot.iss').read_text(encoding='utf-8')
        self.assertIn('AppId={{6A4AD303-4F16-4ED7-A9AF-5B912352D83E}',installer)
        self.assertIn('AppName=Image Draw Bot',installer)
        self.assertIn('ImageDrawBot.exe',installer)
        self.assertIn('/RELAUNCHIMAGEDRAWBOT',installer)
        self.assertIn('/RELAUNCHDRAWSTUDIO',installer)
        self.assertFalse((ROOT/'installer'/'DrawStudio.iss').exists())
        self.assertTrue((ROOT/'ImageDrawBot.manifest').exists())
        self.assertFalse((ROOT/'DrawStudio.manifest').exists())

    def test_build_and_release_names(self):
        build=(ROOT/'build_exe.py').read_text(encoding='utf-8')
        release=(ROOT/'build_release.py').read_text(encoding='utf-8')
        workflow=(ROOT/'.github'/'workflows'/'build-windows.yml').read_text(encoding='utf-8')
        self.assertIn("'--name', 'ImageDrawBot'",build)
        self.assertIn('dist" / "ImageDrawBot',release)
        self.assertIn('ImageDrawBot-${{ github.ref_name }}-Windows-x64',workflow)

    def test_legacy_installed_exe_is_recognized(self):
        from pathlib import Path as RealPath
        with mock.patch('pathlib.Path.glob', return_value=[RealPath('C:/Apps/unins000.exe')]):
            args=UpdateCenter.installer_launch_args('setup.exe',executable='C:/Apps/Draw Studio/DrawStudio.exe')
        self.assertIn('/RELAUNCHIMAGEDRAWBOT',args)

if __name__=='__main__': unittest.main()
