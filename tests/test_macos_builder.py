"""Tests for macOS build-kit generation on any host operating system."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.services.macos_builder import create_macos_build_kit


class MacOSBuildKitTests(unittest.TestCase):
    def test_java_kit_contains_jpackage_script_and_jar(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar = root / "Example.jar"
            jar.write_bytes(b"fake jar for packaging test")
            output = root / "out"
            kit = create_macos_build_kit(kind="java", source=str(jar), output=str(output), name="ExampleApp")
            with zipfile.ZipFile(kit) as archive:
                names = archive.namelist()
                self.assertIn("ExampleApp_macOS_Build_Kit/source/Example.jar", names)
                script = archive.read("ExampleApp_macOS_Build_Kit/build_macos.sh").decode()
                self.assertIn("jpackage --type dmg", script)
                self.assertIn("ExampleApp_Setup.dmg", script)
                readme = archive.read("ExampleApp_macOS_Build_Kit/README_MACOS.txt").decode()
                self.assertIn("JDK", readme)

    def test_python_kit_excludes_dev_folders_and_includes_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "Project"
            (project / "assets").mkdir(parents=True)
            (project / ".venv" / "Lib").mkdir(parents=True)
            (project / ".idea").mkdir()
            (project / "tests").mkdir()
            (project / "main.py").write_text("print('hello')", encoding="utf-8")
            (project / "assets" / "icon.png").write_bytes(b"asset")
            (project / ".venv" / "Lib" / "noise.py").write_text("bad", encoding="utf-8")
            (project / ".idea" / "workspace.xml").write_text("bad", encoding="utf-8")
            (project / "tests" / "test_app.py").write_text("bad", encoding="utf-8")
            (project / "requirements.txt").write_text("", encoding="utf-8")
            kit = create_macos_build_kit(kind="python", source=str(project), output=str(root / "out"), name="ExampleApp")
            with zipfile.ZipFile(kit) as archive:
                names = archive.namelist()
                prefix = "ExampleApp_macOS_Build_Kit/"
                self.assertIn(prefix + "source/main.py", names)
                self.assertIn(prefix + "source/assets/icon.png", names)
                self.assertIn(prefix + "source/requirements.txt", names)
                self.assertFalse(any(".venv" in name or ".idea" in name or "/tests/" in name for name in names))
                self.assertIn(prefix + "build_python_macos.py", names)
                self.assertIn("hdiutil", archive.read(prefix + "build_python_macos.py").decode())




    def test_python_kit_excludes_local_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "Project"
            project.mkdir()
            (project / "main.py").write_text("print('hello')", encoding="utf-8")
            (project / ".env").write_text("API_KEY=secret", encoding="utf-8")
            (project / ".env.production").write_text("SECRET=secret", encoding="utf-8")
            (project / "credentials.json").write_text('{"private_key":"secret"}', encoding="utf-8")
            (project / "private.pem").write_text("PRIVATE KEY", encoding="utf-8")
            kit = create_macos_build_kit(kind="python", source=str(project), output=str(root / "out"), name="SafeApp")
            with zipfile.ZipFile(kit) as archive:
                names = archive.namelist()
                self.assertIn("SafeApp_macOS_Build_Kit/source/main.py", names)
                self.assertFalse(any(name.endswith((".env", ".env.production", "credentials.json", "private.pem")) for name in names))

    def test_python_kit_uses_onedir_mode_and_icns_icon(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); project=root/'Project'; project.mkdir()
            (project/'main.py').write_text('print(1)',encoding='utf-8')
            logo=root/'logo.png'; Image.new('RGBA',(64,64),(20,40,60,255)).save(logo)
            kit=create_macos_build_kit(kind='python',source=str(project),output=str(root/'out'),name='IconApp',icon=str(logo))
            with zipfile.ZipFile(kit) as z:
                names=z.namelist(); prefix='IconApp_macOS_Build_Kit/'
                self.assertIn(prefix+'resources/app.icns',names)
                self.assertIn("'--onedir'",z.read(prefix+'build_python_macos.py').decode())
                self.assertNotIn('onefile.txt', names)

if __name__ == "__main__":
    unittest.main()
