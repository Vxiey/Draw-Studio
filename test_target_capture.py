import json
import subprocess
import unittest
from unittest.mock import patch

import TargetCapture


class Result:
    def __init__(self,code=0,stdout='',stderr=''):
        self.returncode=code;self.stdout=stdout;self.stderr=stderr


class TargetCaptureTests(unittest.TestCase):
    def test_success_returns_handle_and_rect(self):
        out=json.dumps({'ok':True,'handle':12345,'rect':[10,20,900,700],'client_rect':[18,52,892,692],'target_pid':2468})+'\n'
        with patch.object(TargetCapture.subprocess,'run',return_value=Result(0,out)) as run:
            target=TargetCapture.capture_target_isolated((100,120,400,300),exclude_pid=777)
        self.assertEqual(target,(12345,(10,20,900,700)))
        args=run.call_args.args[0]
        self.assertIn('--exclude-pid',args);self.assertIn('777',args)

    def test_helper_validation_error_is_forwarded(self):
        out=json.dumps({'ok':False,'error':'The drawing area is covered by different windows.'})+'\n'
        with patch.object(TargetCapture.subprocess,'run',return_value=Result(2,out)):
            with self.assertRaisesRegex(ValueError,'covered by different windows'):
                TargetCapture.capture_target_isolated((1,2,300,200))

    def test_native_access_violation_becomes_python_error(self):
        with patch.object(TargetCapture.subprocess,'run',return_value=Result(-1073741819,'')):
            with self.assertRaisesRegex(OSError,'0xC0000005'):
                TargetCapture.capture_target_isolated((1,2,300,200))

    def test_timeout_becomes_interrupted_error(self):
        with patch.object(TargetCapture.subprocess,'run',side_effect=subprocess.TimeoutExpired(['python'],8)):
            with self.assertRaisesRegex(InterruptedError,'took too long'):
                TargetCapture.capture_target_isolated((1,2,300,200))

    def test_malformed_success_is_rejected(self):
        out=json.dumps({'ok':True,'handle':'bad','rect':[1,2,3],'client_rect':[1,2,3,4]})+'\n'
        with patch.object(TargetCapture.subprocess,'run',return_value=Result(0,out)):
            with self.assertRaisesRegex(OSError,'invalid window data'):
                TargetCapture.capture_target_isolated((1,2,300,200))

    def test_metadata_and_known_handle_probe(self):
        out=json.dumps({'ok':True,'handle':12345,'rect':[10,20,900,700],'client_rect':[18,52,892,692],'target_pid':2468})+'\n'
        with patch.object(TargetCapture.subprocess,'run',return_value=Result(0,out)) as run:
            meta=TargetCapture.probe_handle_isolated(12345)
        self.assertEqual(meta['client_rect'],(18,52,892,692))
        self.assertEqual(meta['target_pid'],2468)
        self.assertIn('--handle',run.call_args.args[0])


if __name__=='__main__':unittest.main()
