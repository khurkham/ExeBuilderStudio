"""Tests for native Windows installer script generation without running tools."""
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from app.services.windows_native_builder import _find_jpackage, _write_java_installer_script, resolve_jdk_home, _run


class WindowsNativeBuilderTests(unittest.TestCase):
    def test_java_installer_uses_inno_setup_and_app_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app_image = root / "app-image" / "DemoApp"
            app_image.mkdir(parents=True)
            (app_image / "DemoApp.exe").write_bytes(b"MZ")
            (app_image / "runtime").mkdir()
            script = _write_java_installer_script(app_image, "DemoApp", root / "output")
            content = script.read_text(encoding="utf-8-sig")
            self.assertIn("OutputBaseFilename=DemoApp_Setup", content)
            self.assertIn('Source: "' + str(app_image / "*") + '"', content)
            self.assertIn('Filename: "{app}\\DemoApp.exe"', content)
            self.assertIn("PrivilegesRequired=lowest", content)
            self.assertNotIn("WiX", content)
            self.assertNotIn("PowerShell", content)


    def test_jdk_home_is_detected_from_java_home(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "jdk-25"
            (home / "bin").mkdir(parents=True)
            tool = home / "bin" / "jpackage.exe"
            tool.write_bytes(b"MZ")
            with patch.dict(os.environ, {"JAVA_HOME": str(home)}, clear=False), \
                 patch("app.services.windows_native_builder.shutil.which", return_value=None):
                self.assertEqual(resolve_jdk_home(), str(home.resolve()))
                self.assertEqual(_find_jpackage(), str(tool.resolve()))

    def test_java_runtime_shim_is_not_accepted_as_jdk_home(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "Common Files" / "Oracle" / "Java" / "javapath"
            runtime.mkdir(parents=True)
            java = runtime / "java.exe"
            java.write_bytes(b"MZ")
            with patch.dict(os.environ, {"JAVA_HOME": str(runtime.parent.parent)}, clear=False), \
                 patch("app.services.windows_native_builder.shutil.which", return_value=None):
                self.assertEqual(resolve_jdk_home(str(java)), "")


    def test_run_streams_logs_and_reports_progress(self):
        import sys
        logs = []
        progress = []
        with tempfile.TemporaryDirectory() as temp:
            _run([sys.executable, "-c", "print('phase one'); print('phase two')"],
                 cwd=Path(temp), log=logs.append,
                 progress=lambda value, phase: progress.append((value, phase)),
                 progress_range=(10, 20), phase="Testing build progress")
        self.assertTrue(any("phase one" in line for line in logs))
        self.assertTrue(any("phase two" in line for line in logs))
        self.assertEqual(progress[0], (10, "Testing build progress"))
        self.assertEqual(progress[-1], (20, "Testing build progress"))
        self.assertGreaterEqual(max(value for value, _ in progress), 11)

    def test_missing_jpackage_error_explains_runtime_vs_jdk(self):
        with patch("app.services.windows_native_builder.shutil.which", return_value="C:/Java/bin/java.exe"), \
             patch("app.services.windows_native_builder.resolve_jdk_home", return_value=""), \
             patch("app.services.windows_native_builder.subprocess.run") as run:
            run.return_value.stderr = 'java version "25.0.3"'
            run.return_value.stdout = ''
            with self.assertRaisesRegex(FileNotFoundError, "full JDK containing jpackage.exe"):
                _find_jpackage()


if __name__ == "__main__":
    unittest.main()
