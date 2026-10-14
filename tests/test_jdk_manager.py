"""Tests for explicit JDK selection and version validation."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.jdk_manager import jdk_version, validate_jdk_home
from app.services.windows_native_builder import _find_jpackage


class JdkManagerTests(unittest.TestCase):
    def test_validates_selected_jdk_and_reads_release_version(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "jdk-21"
            (home / "bin").mkdir(parents=True)
            (home / "bin" / ("jpackage.exe" if os.name == "nt" else "jpackage")).write_bytes(b"MZ")
            (home / "release").write_text('JAVA_VERSION="21.0.5"\n', encoding="utf-8")
            self.assertEqual(jdk_version(home), "21.0.5")
            self.assertEqual(validate_jdk_home(home), (True, "21.0.5"))

    def test_rejects_jdk_older_than_17(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "jdk-11"
            (home / "bin").mkdir(parents=True)
            (home / "bin" / ("jpackage.exe" if os.name == "nt" else "jpackage")).write_bytes(b"MZ")
            (home / "release").write_text('JAVA_VERSION="11.0.24"\n', encoding="utf-8")
            valid, message = validate_jdk_home(home)
            self.assertFalse(valid)
            self.assertIn("JDK 17 or newer", message)

    def test_selected_jdk_is_used_for_jpackage(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "jdk-25"
            (home / "bin").mkdir(parents=True)
            tool = home / "bin" / "jpackage.exe"
            tool.write_bytes(b"MZ")
            (home / "release").write_text('JAVA_VERSION="25.0.3"\n', encoding="utf-8")
            self.assertEqual(_find_jpackage(str(home)), str(tool.resolve()))

    def test_selected_folder_without_jpackage_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "not-a-jdk"
            home.mkdir()
            with self.assertRaisesRegex(FileNotFoundError, "does not contain jpackage.exe"):
                _find_jpackage(str(home))


if __name__ == "__main__":
    unittest.main()
