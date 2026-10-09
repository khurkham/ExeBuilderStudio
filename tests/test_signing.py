import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import signing


class SigningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.exe = self.root / "โปรแกรม test & 'name.exe"
        self.exe.write_bytes(b'MZ')
        self.thumb = 'AB' * 20

    def tearDown(self):
        self.temp.cleanup()

    def test_store_signing_uses_sha256_and_separate_arguments(self):
        args = signing.sign_arguments(self.exe, self.thumb)
        self.assertEqual(args[:7], ['sign', '/v', '/fd', 'SHA256', '/s', 'My', '/sha1'])
        self.assertEqual(args[7], self.thumb)
        self.assertEqual(args[-1], str(self.exe.resolve()))
        self.assertNotIn('/p', args)
        self.assertNotIn('/sm', args)

    def test_machine_store_and_timestamp(self):
        args = signing.sign_arguments(self.exe, self.thumb, 'http://timestamp.digicert.com', True)
        self.assertIn('/sm', args)
        self.assertEqual(args[args.index('/td')+1], 'SHA256')
        self.assertEqual(args[args.index('/tr')+1], 'http://timestamp.digicert.com')

    def test_missing_file_and_bad_thumbprint_abort(self):
        with self.assertRaises(ValueError):
            signing.sign_arguments(self.root / 'missing.exe', self.thumb)
        for value in ('', 'Z'*40, 'AB'*19, 'AB'*21, 'abc;Write-Host bad'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                signing.sign_arguments(self.exe, value)
        self.assertEqual(signing.thumbprint('ab '*20), self.thumb)

    def test_invalid_timestamp_abort(self):
        for url in ('file:///tmp/x', 'https://', 'https://user:password@example.com', 'http://example.com/ space'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                signing.sign_arguments(self.exe, self.thumb, url)

    def test_verification_uses_authenticode_policy(self):
        self.assertEqual(signing.verify_arguments(self.exe), ['verify', '/pa', '/all', '/v', str(self.exe.resolve())])

    def test_parse_result_ignores_other_output(self):
        expected = {'thumbprint': self.thumb, 'publisher': 'ၶုၼ်ၶမ်း'}
        text = 'SDK installer completed\nEBS_JSON:' + json.dumps(expected) + '\n'
        self.assertEqual(signing.parse_result(text), expected)
        with self.assertRaises(ValueError):
            signing.parse_result('Installer failed')
        self.assertEqual(signing.parse_result('EBS_JSON:[]'), [])

    def test_native_architecture_and_numerical_sdk_version(self):
        for version, arch in [('10.0.9999.0','x64'), ('10.0.10000.0','x64'), ('10.0.20000.0','x86')]:
            exe = self.root / 'Windows Kits/10/bin' / version / arch / 'signtool.exe'
            exe.parent.mkdir(parents=True); exe.write_bytes(b'MZ')
        with patch.dict(os.environ, {'ProgramFiles(x86)':str(self.root),'ProgramFiles':str(self.root)}), \
             patch('signing.shutil.which',return_value=None), patch('signing.platform.machine',return_value='AMD64'):
            self.assertEqual(Path(signing.detect_signtool()).parent.parent.name, '10.0.10000.0')
            self.assertEqual(Path(signing.detect_signtool()).parent.name, 'x64')

    def test_pwsh_command_contains_no_secrets(self):
        exe, args = signing.powershell_command()
        self.assertTrue(exe.endswith('powershell.exe'))
        self.assertEqual(args[-2], '-File')
        self.assertTrue(Path(args[-1]).is_file())
        self.assertNotIn('-Command', args)

    def test_installer_hooks_only_studio_and_contains_no_private_key(self):
        root = Path(__file__).resolve().parents[1]
        script = (root/'installer/ExeBuilderStudio.iss').read_text()
        self.assertIn('AppVersion=1.0',script)
        self.assertIn('Ensure-Certificate.ps1',script)
        self.assertIn('waituntilterminated',script)
        self.assertNotIn('TrustedRoot',script)
        from backend import inno_script
        generated = inno_script(self.root,self.exe.name,'AnimalDiceGame','1.0','Khurkham',self.root/'setup')
        self.assertNotIn('Ensure-Certificate',generated.read_text(encoding='utf-8-sig'))


if __name__=='__main__':
    unittest.main()
