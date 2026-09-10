import hashlib
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from UpdateCenter import installer_asset,download_installer,installer_launch_args,UpdateCheckError

try:
    from DrawBot import DrawBotApp
except ModuleNotFoundError:
    DrawBotApp=None

DATA=b'MZ'+b'verified-test-installer'*100

def release():
    name='ImageDrawBot-1.0.134-rc1-Windows-x64-Setup.exe'
    return dict(tag_name='v1.0.134-rc1',assets=[dict(name=name,size=len(DATA),digest='sha256:'+hashlib.sha256(DATA).hexdigest(),browser_download_url='https://github.com/Vxiey/Image-Draw-Bot/releases/download/v1.0.134-rc1/'+name)])

class Response:
    url='https://release-assets.githubusercontent.com/file'
    def __init__(self,data=DATA):self.data=data;self.closed=False
    def raise_for_status(self):pass
    def iter_content(self,chunk_size):yield self.data[:20];yield self.data[20:]
    def close(self):self.closed=True

class InstallerUpdateTests(unittest.TestCase):
    def test_exact_asset_and_digest_required(self):
        self.assertIsNotNone(installer_asset(release()))
        for key,value in [('name','evil.exe'),('digest',None),('size',0),('browser_download_url','https://example.com/a.exe')]:
            item=release();item['assets'][0][key]=value
            self.assertIsNone(installer_asset(item))
        item=release();item['assets']*=2
        self.assertIsNone(installer_asset(item))

    def test_download_size_hash_and_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            response=Response();progress=[]
            path=download_installer(installer_asset(release()),directory=tmp,request_get=lambda *a,**k:response,progress=lambda a,b:progress.append((a,b)))
            self.assertEqual(Path(path).read_bytes(),DATA)
            self.assertTrue(response.closed)
            self.assertEqual(progress[-1],(len(DATA),len(DATA)))
            self.assertFalse(list(Path(tmp).glob('*.part')))

    def test_corrupt_truncated_and_oversized_never_leave_executable(self):
        for content in (DATA[:-1],DATA+b'bad',DATA[:-1]+b'X'):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(UpdateCheckError):
                    download_installer(installer_asset(release()),directory=tmp,request_get=lambda *a,**k:Response(content))
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_stop_during_download_cleans_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop=threading.Event()
            with self.assertRaises(InterruptedError):
                download_installer(installer_asset(release()),directory=tmp,request_get=lambda *a,**k:Response(),cancelled=stop.is_set,progress=lambda *a:stop.set())
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_unexpected_redirect_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            response=Response();response.url='https://example.com/file'
            with self.assertRaises(UpdateCheckError):
                download_installer(installer_asset(release()),directory=tmp,request_get=lambda *a,**k:response)
            self.assertTrue(response.closed)

    def test_stale_or_cancelled_ui_handoff_does_not_install(self):
        if DrawBotApp is None:self.skipTest('DrawBot GUI dependencies are not installed')
        token=object();app=SimpleNamespace(closing=False,stop=threading.Event(),update_request=token)
        self.assertFalse(DrawBotApp._install_checked_update(app,{'request':object()}))
        app.stop.set()
        self.assertFalse(DrawBotApp._install_checked_update(app,{'request':token}))


    def test_installed_build_uses_silent_in_place_relaunch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);setup=root/'setup.exe';setup.write_bytes(DATA)
            executable=root/'ImageDrawBot.exe';(root/'unins000.exe').write_bytes(b'MZ')
            args=installer_launch_args(setup,executable=executable)
            self.assertIn('/DIR='+str(root),args)
            for flag in ('/VERYSILENT','/SUPPRESSMSGBOXES','/CLOSEAPPLICATIONS','/RELAUNCHIMAGEDRAWBOT','/NORESTART'):
                self.assertIn(flag,args)
            self.assertNotIn('/FORCECLOSEAPPLICATIONS',args)

    def test_portable_build_never_overwrites_itself_or_forces_silent_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);setup=root/'setup.exe';executable=root/'ImageDrawBot.exe'
            args=installer_launch_args(setup,executable=executable)
            self.assertFalse(any(arg.startswith('/DIR=') for arg in args))
            self.assertNotIn('/VERYSILENT',args)
            self.assertNotIn('/RELAUNCHIMAGEDRAWBOT',args)

    @unittest.skipUnless(__import__('os').name=='nt','Windows installer handoff')
    def test_installer_launch_rechecks_bytes_and_preserves_install_directory(self):
        from UpdateCenter import launch_installer
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);setup=root/'setup.exe';setup.write_bytes(DATA)
            executable=root/'ImageDrawBot.exe';(root/'unins000.exe').write_bytes(b'MZ')
            calls=[];asset=installer_asset(release())
            launch_installer(setup,asset,executable=executable,launcher=lambda args:calls.append(args))
            self.assertIn('/DIR='+str(root),calls[0])
            self.assertIn('/NORESTART',calls[0])
            self.assertIn('/VERYSILENT',calls[0])
            self.assertIn('/RELAUNCHIMAGEDRAWBOT',calls[0])
            setup.write_bytes(DATA[:-1]+b'X')
            with self.assertRaises(UpdateCheckError):launch_installer(setup,asset,launcher=lambda args:self.fail('must not execute'))

if __name__=='__main__':unittest.main()
