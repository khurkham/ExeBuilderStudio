"""Regression tests for native macOS app packaging support."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.services.jdk_manager import bundled_jdk_home, discover_jdk_homes


class MacDistributionTests(unittest.TestCase):
    def test_release_script_is_native_only_and_builds_app_and_dmg(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "macos" / "build_macos_distribution.sh").read_text(encoding="utf-8")
        self.assertIn('uname -s', script)
        self.assertIn('ExeBuilderStudio.app', script)
        self.assertIn('hdiutil create', script)
        self.assertIn('command -v create-dmg', script)
        self.assertIn('--app-drop-link', script)
        self.assertIn('--windowed --onedir', script)
        self.assertIn('EBS_BUNDLE_JDK_HOME', script)
        self.assertNotIn('GitHub Actions', script)

    def test_bundled_jdk_is_discovered_inside_macos_app(self):
        with tempfile.TemporaryDirectory() as temp:
            contents = Path(temp) / "ExeBuilderStudio.app" / "Contents"
            executable = contents / "MacOS" / "ExeBuilderStudio"
            executable.parent.mkdir(parents=True)
            executable.write_text("placeholder", encoding="utf-8")
            jdk = contents / "Resources" / "tools" / "jdk"
            (jdk / "bin").mkdir(parents=True)
            (jdk / "bin" / "jpackage").write_text("placeholder", encoding="utf-8")
            (jdk / "release").write_text('JAVA_VERSION="21.0.5"\n', encoding="utf-8")
            with patch.object(sys, "platform", "darwin"), \
                 patch.object(sys, "executable", str(executable)), \
                 patch.object(sys, "frozen", True, create=True):
                self.assertEqual(bundled_jdk_home(), jdk)
                matches = discover_jdk_homes()
                self.assertTrue(any(path == str(jdk) for _, path in matches))

    def test_bundled_jdk_not_assumed_when_running_from_source(self):
        with patch.object(sys, "platform", "darwin"), \
             patch.object(sys, "frozen", False, create=True):
            self.assertIsNone(bundled_jdk_home())


if __name__ == "__main__":
    unittest.main()
