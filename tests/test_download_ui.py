import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
import main,download_ui as ui
class DownloadUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.tmp=tempfile.TemporaryDirectory();QSettings.setDefaultFormat(QSettings.IniFormat);QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,cls.tmp.name);QSettings.setPath(QSettings.NativeFormat,QSettings.UserScope,cls.tmp.name)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        QSettings('Khurkham','ExeBuilderStudio').clear();self.window=main.Window();self.card=self.window.tool_cards[0];self.window.lang.setCurrentIndex(1)
    def tearDown(self):self.window.busy=False;self.window.close();self.app.processEvents()
    def test_all_tools_and_about_have_check_download_update_install(self):
        self.assertEqual([c.key for c in self.window.tool_cards],['java','launch4j','inno','python','pyinstaller','sdk','studio'])
        for c in self.window.tool_cards:self.assertEqual(set(c.buttons),{'check','download','update','install'})
    def test_missing_status_not_success(self):
        self.card.complete({'detected':{'found':False,'version':'','path':''},'installed':True})
        self.assertIn('กรุณาดาวน์โหลดโปรแกรม',self.card.status.text())
    def test_progress_known_and_unknown_size(self):
        self.card.progress(30,100);self.assertEqual(self.card.bar.value(),30)
        self.card.progress(30,0);self.assertEqual(self.card.bar.maximum(),0)
    def test_completed_check_stops_animation_and_unlocks_ui(self):
        self.card.worker=ui.ToolWorker('java','check');self.window.busy=True
        self.card.bar.show();self.card.bar.setRange(0,0)
        self.card.complete({'detected':{'found':True,'version':'25.0.3','path':'java.exe'}})
        self.card.cleanup()
        self.assertFalse(self.window.busy);self.assertTrue(self.card.bar.isHidden());self.assertEqual(self.card.bar.maximum(),100)
    def test_status_growth_does_not_squeeze_buttons(self):
        self.window.resize(1080,820);self.window.tabs.setCurrentIndex(4);self.window.show();self.app.processEvents()
        self.card.complete({'detected':{'found':True,'version':'java version "25.0.3"\nJava Runtime Environment\nJava HotSpot VM','path':'C:/Program Files/Java/bin/java.exe'}})
        self.app.processEvents()
        for button in self.card.buttons.values():
            self.assertGreaterEqual(button.height(),button.fontMetrics().height()+24)
        self.assertGreater(self.window.tabs.widget(4).widget().minimumHeight(),self.window.tabs.widget(4).viewport().height())
    def test_about_has_no_end_user_update_source_controls(self):
        self.assertFalse(hasattr(self.window,'update_repo'))
        self.assertFalse(hasattr(self.window,'update_label'))
        self.assertFalse(hasattr(self.window,'update_save'))
        self.window.settings.setValue('updates/repository','Untrusted/UserSetting')
        with patch.object(ui,'UPDATE_REPOSITORY',''):
            studio=self.window.tool_cards[-1];studio.begin('update')
        self.assertEqual(studio.state,'notconfigured');self.assertIn('ผู้พัฒนา',studio.status.text())
    def test_missing_self_update_source_stays_in_app(self):
        studio=self.window.tool_cards[-1];studio.begin('update')
        self.assertEqual(studio.state,'notconfigured');self.assertFalse(self.window.busy)
    def test_pip_directory_can_be_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            worker=ui.ToolWorker('pyinstaller','install',configured='python',artifact={'path':directory,'release':{'kind':'pip'}})
            results=[];failures=[];worker.result.connect(results.append);worker.failed.connect(failures.append)
            with patch.object(worker,'run_pip') as pip,patch.object(ui,'detect_tool',return_value={'found':True,'version':'6.16','path':'python'}):worker.run()
            self.assertFalse(failures);self.assertTrue(results[0]['installed']);self.assertIn('--no-index',pip.call_args.args[0])
    def test_latest_version_skips_download(self):
        worker=ui.ToolWorker('studio','update',repo='Owner/Repo');results=[];worker.result.connect(results.append)
        with patch.object(ui,'resolve_release',return_value={'version':'1.0'}),patch.object(ui,'detect_tool',return_value={'found':True,'version':'1.0','path':'app.exe'}),patch.object(ui,'download') as download:worker.run()
        self.assertTrue(results[0]['current']);download.assert_not_called()
    def test_new_update_installs_only_after_valid_download_result(self):
        self.card.worker=ui.ToolWorker('java','update');self.card.complete({'artifact':{'path':'test.zip','release':{'kind':'zip','version':'25.0.1'},'digest':'a'*64}})
        self.assertTrue(self.card.install_after_update)
        with patch.object(ui.QTimer,'singleShot') as timer:self.card.cleanup()
        timer.assert_called_once();self.assertFalse(self.window.busy)
    def test_cancel_uses_worker_instead_of_build_process(self):
        self.window.active_download=self.card;self.card.worker=ui.ToolWorker('java','download');self.window.busy=True
        with patch.object(self.card.worker,'cancel') as cancel,patch.object(self.window.process,'kill') as kill:self.window.cancel()
        cancel.assert_called_once();kill.assert_not_called()
        self.card.worker=None
if __name__=='__main__':unittest.main()
