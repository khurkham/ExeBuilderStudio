"""Tests for portable Windows build kits prepared on any host OS."""
import tempfile, unittest, zipfile
from pathlib import Path
from app.services.windows_builder import create_windows_build_kit

class WindowsBuildKitTests(unittest.TestCase):
    def test_java_kit_uses_jpackage_and_windows_native_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); jar=root/'Example.jar'; jar.write_bytes(b'jar')
            kit=create_windows_build_kit(kind='java', source=str(jar), output=str(root/'out'), name='ExampleApp')
            with zipfile.ZipFile(kit) as z:
                names=z.namelist(); prefix='ExampleApp_Windows_Build_Kit/'
                self.assertIn(prefix+'source/Example.jar', names)
                script=z.read(prefix+'build_windows.ps1').decode('utf-8-sig')
                self.assertIn('jpackage --type exe',script)
                self.assertIn('WiX Toolset',script)
                self.assertIn(prefix+'README_WINDOWS.txt',names)
    def test_python_kit_filters_dev_folders_and_keeps_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/'Project'; (project/'assets').mkdir(parents=True)
            (project/'.venv'/'Lib').mkdir(parents=True); (project/'.idea').mkdir(); (project/'tests').mkdir()
            (project/'main.py').write_text('print(1)',encoding='utf-8')
            (project/'assets'/'image.png').write_bytes(b'png'); (project/'requirements.txt').write_text('',encoding='utf-8')
            (project/'.venv'/'Lib'/'junk.py').write_text('bad'); (project/'.idea'/'workspace.xml').write_text('bad'); (project/'tests'/'test_x.py').write_text('bad')
            kit=create_windows_build_kit(kind='python',source=str(project),output=str(root/'out'),name='ExampleApp')
            with zipfile.ZipFile(kit) as z:
                names=z.namelist(); prefix='ExampleApp_Windows_Build_Kit/'
                self.assertIn(prefix+'source/main.py',names); self.assertIn(prefix+'source/assets/image.png',names)
                self.assertFalse(any('.venv' in n or '.idea' in n or '/tests/' in n for n in names))
                self.assertIn(prefix+'build_python_windows.py',names)
                self.assertIn('ISCC.exe',z.read(prefix+'build_windows.ps1').decode('utf-8-sig'))

    def test_python_kit_uses_onedir_mode_and_custom_ico(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/'Project'; project.mkdir()
            (project/'main.py').write_text('print(1)',encoding='utf-8')
            logo=root/'logo.png'; Image.new('RGBA',(64,64),(20,40,60,255)).save(logo)
            kit=create_windows_build_kit(kind='python',source=str(project),output=str(root/'out'),name='IconApp',icon=str(logo))
            with zipfile.ZipFile(kit) as z:
                names=z.namelist(); prefix='IconApp_Windows_Build_Kit/'
                self.assertIn(prefix+'resources/app.ico',names)
                self.assertIn("'--onedir'",z.read(prefix+'build_python_windows.py').decode())
                self.assertNotIn('onefile.txt', names)
                self.assertIn('SetupIconFile="resources\\app.ico"',z.read(prefix+'installer.iss').decode('utf-8-sig'))

if __name__=='__main__': unittest.main()
