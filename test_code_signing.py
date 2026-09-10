import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from CodeSigning import signing_configuration,SigningError,sign_distribution,sign_file,inno_arguments

class CodeSigningTests(unittest.TestCase):
    def test_missing_certificate_blocks_signed_build(self):
        with self.assertRaises(SigningError):signing_configuration({})

    def test_config_validates_thumbprint_and_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool=Path(tmp)/'signtool.exe';tool.touch()
            conf=signing_configuration({'IMAGEDRAWBOT_SIGNTOOL':str(tool),'IMAGEDRAWBOT_SIGNING_THUMBPRINT':'ab'*20})
            self.assertEqual(conf[1],'AB'*20)
            with self.assertRaises(SigningError):signing_configuration({'IMAGEDRAWBOT_SIGNTOOL':str(tool),'IMAGEDRAWBOT_SIGNING_THUMBPRINT':'bad; command'})

    def test_dependencies_signed_and_upstream_signature_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('ImageDrawBot.exe','python.dll','extension.pyd','data.txt'):(root/name).touch()
            with patch('CodeSigning.verify',return_value=True),patch('CodeSigning.sign_file') as sign:
                self.assertEqual(sign_distribution(root,('tool','AA'*20)),3)
                self.assertEqual([c.args[0].name for c in sign.call_args_list],['ImageDrawBot.exe'])
            with patch('CodeSigning.verify',side_effect=[False,False,True,True,True]),patch('CodeSigning.sign_file') as sign:
                sign_distribution(root,('tool','AA'*20))
                self.assertEqual(sign.call_count,3)

    def test_timestamp_and_authenticode_verification_required(self):
        with patch('CodeSigning.subprocess.run') as run:
            sign_file(Path('app.exe'),('tool','AA'*20))
        self.assertIn('/tr',run.call_args_list[0].args[0])
        self.assertIn('SHA256',run.call_args_list[0].args[0])
        self.assertIn('/tw',run.call_args_list[1].args[0])
        self.assertTrue(run.call_args_list[1].kwargs['check'])

    def test_inno_signs_installer_and_uninstaller(self):
        args=inno_arguments(('C:/Windows SDK/signtool.exe','AA'*20))
        self.assertIn('/DSignRelease',args)
        self.assertIn('$qC:/Windows SDK/signtool.exe$q',args[1])
        self.assertTrue(args[1].endswith('$f'))

if __name__=='__main__':unittest.main()
