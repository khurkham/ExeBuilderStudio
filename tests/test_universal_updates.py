"""Tests for cross-platform GitHub release asset selection."""
import unittest
from unittest.mock import patch

from app.services import universal_updates


class UniversalUpdateTests(unittest.TestCase):
    def asset(self, name):
        return {
            "name": name,
            "browser_download_url": "https://github.com/khurkham/ExeBuilderStudio/releases/download/v1.3/" + name,
            "digest": "sha256:" + "b" * 64,
            "size": 1234,
        }

    def release(self, assets):
        return {"draft": False, "prerelease": False, "tag_name": "v1.3", "assets": assets}

    @patch("app.services.universal_updates._json")
    @patch("app.services.universal_updates.platform.machine", return_value="AMD64")
    @patch("app.services.universal_updates.os.name", "nt")
    @patch("app.services.universal_updates.sys.platform", "win32")
    def test_selects_windows_setup_exe(self, _machine, get_json):
        get_json.return_value = self.release([
            self.asset("ExeBuilderStudio-1.3-macOS-arm64.dmg"),
            self.asset("ExeBuilderStudio_Setup.exe"),
        ])
        result = universal_updates.current_platform_asset()
        self.assertEqual(result["kind"], "exe")
        self.assertEqual(result["name"], "ExeBuilderStudio_Setup.exe")
        self.assertEqual(result["sha256"], "b" * 64)

    @patch("app.services.universal_updates._json")
    @patch("app.services.universal_updates.platform.machine", return_value="arm64")
    @patch("app.services.universal_updates.os.name", "posix")
    @patch("app.services.universal_updates.sys.platform", "darwin")
    def test_selects_arm64_dmg(self, _machine, get_json):
        get_json.return_value = self.release([
            self.asset("ExeBuilderStudio-1.3-macOS-x86_64.dmg"),
            self.asset("ExeBuilderStudio-1.3-macOS-arm64.dmg"),
        ])
        result = universal_updates.current_platform_asset()
        self.assertEqual(result["kind"], "dmg")
        self.assertEqual(result["architecture"], "arm64")

    @patch("app.services.universal_updates._json")
    @patch("app.services.universal_updates.platform.machine", return_value="x86_64")
    @patch("app.services.universal_updates.os.name", "posix")
    @patch("app.services.universal_updates.sys.platform", "darwin")
    def test_selects_intel_dmg(self, _machine, get_json):
        get_json.return_value = self.release([
            self.asset("ExeBuilderStudio-1.3-macOS-arm64.dmg"),
            self.asset("ExeBuilderStudio-1.3-macOS-x86_64.dmg"),
        ])
        result = universal_updates.current_platform_asset()
        self.assertEqual(result["kind"], "dmg")
        self.assertEqual(result["architecture"], "x86_64")

    @patch("app.services.universal_updates._json")
    @patch("app.services.universal_updates.platform.machine", return_value="arm64")
    @patch("app.services.universal_updates.os.name", "posix")
    @patch("app.services.universal_updates.sys.platform", "darwin")
    def test_fails_when_matching_dmg_missing(self, _machine, get_json):
        get_json.return_value = self.release([self.asset("ExeBuilderStudio-1.3-macOS-x86_64.dmg")])
        with self.assertRaisesRegex(ValueError, "does not contain the required macOS arm64 DMG"):
            universal_updates.current_platform_asset()

    @patch("app.services.universal_updates._json")
    @patch("app.services.universal_updates.platform.machine", return_value="AMD64")
    @patch("app.services.universal_updates.os.name", "nt")
    @patch("app.services.universal_updates.sys.platform", "win32")
    def test_rejects_missing_sha256(self, _machine, get_json):
        item = self.asset("ExeBuilderStudio_Setup.exe")
        item["digest"] = ""
        get_json.return_value = self.release([item])
        with self.assertRaisesRegex(ValueError, "no valid GitHub SHA-256 digest"):
            universal_updates.current_platform_asset()


if __name__ == "__main__":
    unittest.main()
