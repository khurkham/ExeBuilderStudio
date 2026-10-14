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
        # Only seed fields that exist in the current UI; Launch4j was removed.
        for key in ['tools/launch4jc','tools/ISCC','tools/Python interpreter']:
            if key in self.window.fields:
                self.window.fields[key].setText(str(self.tool))

    def tearDown(self):
        self.window.busy=False; self.window.close(); self.window.deleteLater()
        self.app.processEvents(); self.temp.cleanup()

    def field(self,key,value):self.window.fields[key].setText(str(value))

    def test_failed_process_does_not_run_following_step(self):
        followed=[]; self.window.on_success=lambda output:followed.append(output)
        with patch.object(self.window,'read_output'):
            self.window.finished(1,QProcess.NormalExit)
        self.assertFalse(followed); self.assertIsNone(self.window.on_success)
        self.assertIn('skipped',self.window.status.text())



if __name__=='__main__':unittest.main()
