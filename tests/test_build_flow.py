"""Headless Qt tests of build chaining; no Windows tools are executed."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    from PySide6.QtCore import QSettings, QProcess
    from PySide6.QtWidgets import QApplication
    import main
except ImportError:
    main=None


@unittest.skipIf(main is None, 'Install PySide6 for GUI flow tests')
class BuildFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.settings_directory=tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,cls.settings_directory.name)
        QSettings.setPath(QSettings.NativeFormat,QSettings.UserScope,cls.settings_directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.settings_directory.cleanup()

    def setUp(self):
        QSettings('Khurkham','ExeBuilderStudio').clear()
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name).resolve()
        self.window=main.Window(); self.calls=[]
        self.window.start=lambda exe,args,cwd=None,callback=None,payload=None,label=None:self.calls.append({
            'exe':exe,'args':args,'cwd':cwd,'callback':callback,'payload':payload,'label':label})
        self.tool=self.root/'tool.exe'; self.tool.write_bytes(b'MZ')
        for key in ['tools/launch4jc','tools/ISCC','tools/Python interpreter','signing/signtool']:
            self.window.fields[key].setText(str(self.tool))
        self.window.fields['signing/thumbprint'].setText('AB'*20)
        self.window.fields['signing/autosign'].setChecked(True)

    def tearDown(self):
        self.window.busy=False; self.window.close(); self.window.deleteLater()
        self.app.processEvents(); self.temp.cleanup()

    def field(self,key,value):self.window.fields[key].setText(str(value))

    def test_java_build_then_sign(self):
        jar=self.root/'App.jar'; jar.write_bytes(b'jar')
        self.field('java/source',jar); self.field('java/output',self.root/'out'); self.field('java/name','Game')
        self.window.build_java(); self.assertEqual(len(self.calls),1)
        self.assertTrue(self.calls[0]['args'][0].endswith('launch4j.xml'))
        target=self.root/'out/Game/Game.exe'; target.write_bytes(b'MZ')
        self.calls[0]['callback']('Launch4j success')
        self.assertEqual(self.calls[1]['args'][0],'sign')
        self.assertEqual(self.calls[1]['args'][-1],str(target))

    def test_python_onefile_and_onedir_then_sign(self):
        source=self.root/'game.py'; source.write_text('print(1)')
        for onefile in (True,False):
            self.calls.clear(); out=self.root/('single' if onefile else 'directory')
            self.field('python/source',source); self.field('python/output',out); self.field('python/name','Game')
            self.window.fields['python/onefile'].setChecked(onefile)
            self.window.build_python()
            self.assertIn('--onefile' if onefile else '--onedir',self.calls[0]['args'])
            target=out/'dist/Game.exe' if onefile else out/'dist/Game/Game.exe'
            target.parent.mkdir(parents=True); target.write_bytes(b'MZ')
            self.calls[0]['callback']('PyInstaller success')
            self.assertEqual(self.calls[1]['args'][-1],str(target))

    def test_sign_release_before_inno_and_setup_after_inno(self):
        release=self.root/'release'; release.mkdir(); (release/'Game.exe').write_bytes(b'MZ')
        out=self.root/'installers'
        self.field('installer/folder',release); self.field('installer/output',out)
        self.field('installer/exe','Game.exe'); self.field('installer/name','Game')
        self.window.build_installer()
        self.assertEqual(self.calls[0]['args'][0],'sign')
        self.assertEqual(self.calls[0]['args'][-1],str(release/'Game.exe'))
        self.calls[0]['callback']('Signed app')
        self.assertTrue(self.calls[1]['args'][0].endswith('Game.iss'))
        target=out/'Game_Setup.exe'; target.write_bytes(b'MZ')
        self.calls[1]['callback']('Inno success')
        self.assertEqual(self.calls[2]['args'][0],'sign')
        self.assertEqual(self.calls[2]['args'][-1],str(target))

    def test_failed_process_does_not_run_following_step(self):
        followed=[]; self.window.on_success=lambda output:followed.append(output)
        with patch.object(self.window,'read_output'):
            self.window.finished(1,QProcess.NormalExit)
        self.assertFalse(followed); self.assertIsNone(self.window.on_success)
        self.assertIn('skipped',self.window.status.text())

    def test_password_not_saved_or_logged_and_passed_as_stdin(self):
        path=self.root/'certificate.pfx'; path.write_bytes(b'test')
        password="never-store-'secret-ၶမ်း"
        self.field('signing/pfx',path); self.field('signing/pfxpassword',password)
        self.window.save_settings()
        self.assertFalse(self.window.settings.contains('signing/pfxpassword'))
        self.window.import_certificate()
        self.assertEqual(self.calls[0]['payload']['password'],password)
        self.assertNotIn(password,str(self.calls[0]['args']))
        self.assertNotIn(password,self.window.log.toPlainText())
        self.assertEqual(self.window.fields['signing/pfxpassword'].text(),'')

    def test_certificate_reuse_does_not_replace_commercial_selection(self):
        self.window.signmode.setCurrentIndex(1)
        self.field('signing/thumbprint','CD'*20)
        self.window.certificate_ready('EBS_JSON:{"publisher":"Khurkham","thumbprint":"'+('AB'*20)+'","created":false}')
        self.assertEqual(self.window.v('signing','thumbprint'),'CD'*20)

    def test_certificate_created_only_after_sdk_success_and_detection(self):
        with patch('main.QFileDialog.getOpenFileName',return_value=(str(self.tool),'')), \
             patch('main.detect_signtool',return_value=str(self.tool)):
            self.window.install_sdk()
            self.assertEqual(self.calls[0]['payload']['action'],'install-sdk')
            self.assertEqual(len(self.calls),1)
            self.calls[0]['callback']('EBS_JSON:{"installed":true,"restart_required":false}')
            self.assertEqual(self.calls[1]['payload']['action'],'ensure')

    def test_sdk_without_signing_tools_does_not_claim_success(self):
        with patch('main.QFileDialog.getOpenFileName',return_value=(str(self.tool),'')), \
             patch('main.detect_signtool',return_value=''):
            self.window.install_sdk()
            with self.assertRaisesRegex(ValueError,'SignTool not found'):
                self.calls[0]['callback']('EBS_JSON:{"installed":true}')
            self.assertEqual(len(self.calls),1)


if __name__=='__main__':unittest.main()
