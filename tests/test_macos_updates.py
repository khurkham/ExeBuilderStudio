"""Unit tests for macOS GitHub Release asset selection."""
import unittest
from unittest.mock import patch

from app.services import macos_updates


class MacOSUpdateTests(unittest.TestCase):
    def release_payload(self, assets):
        return {
            "draft": False,
            "prerelease": False,
            "tag_name": "v1.2",
            "html_url": "https://github.com/khurkham/ExeBuilderStudio/releases/tag/v1.2",
            "assets": assets,
        }

    def asset(self, name, digest="sha256:" + "a" * 64):
        return {
            "name": name,
            "browser_download_url": "https://github.com/khurkham/ExeBuilderStudio/releases/download/v1.2/" + name,
            "digest": digest,
            "size": 1024,
        }

    @patch("app.services.macos_updates._get_json")
    @patch("app.services.macos_updates.platform.machine", return_value="arm64")
    def test_selects_matching_apple_silicon_asset(self, _machine, get_json):
        get_json.return_value = self.release_payload([
            self.asset("ExeBuilderStudio-1.2-macOS-x86_64.dmg"),
            self.asset("ExeBuilderStudio-1.2-macOS-arm64.dmg"),
            self.asset("ExeBuilderStudio_Setup.exe"),
        ])
        release = macos_updates.latest_macos_release()
        self.assertEqual(release["version"], "1.2")
        self.assertEqual(release["architecture"], "arm64")
        self.assertEqual(release["name"], "ExeBuilderStudio-1.2-macOS-arm64.dmg")
        self.assertEqual(release["sha256"], "a" * 64)

    @patch("app.services.macos_updates._get_json")
    @patch("app.services.macos_updates.platform.machine", return_value="x86_64")
    def test_selects_matching_intel_asset(self, _machine, get_json):
        get_json.return_value = self.release_payload([
            self.asset("ExeBuilderStudio-1.2-macOS-arm64.dmg"),
            self.asset("ExeBuilderStudio-1.2-macOS-x86_64.dmg"),
        ])
        release = macos_updates.latest_macos_release()
        self.assertEqual(release["architecture"], "x86_64")
        self.assertEqual(release["name"], "ExeBuilderStudio-1.2-macOS-x86_64.dmg")

    @patch("app.services.macos_updates._get_json")
    @patch("app.services.macos_updates.platform.machine", return_value="arm64")
    def test_rejects_release_without_matching_architecture(self, _machine, get_json):
        get_json.return_value = self.release_payload([
            self.asset("ExeBuilderStudio-1.2-macOS-x86_64.dmg"),
        ])
        with self.assertRaisesRegex(ValueError, "No macOS DMG"):
            macos_updates.latest_macos_release()

    @patch("app.services.macos_updates._get_json")
    @patch("app.services.macos_updates.platform.machine", return_value="arm64")
    def test_rejects_asset_without_sha256_digest(self, _machine, get_json):
        get_json.return_value = self.release_payload([
            self.asset("ExeBuilderStudio-1.2-macOS-arm64.dmg", digest=""),
        ])
        with self.assertRaisesRegex(ValueError, "SHA-256 digest"):
            macos_updates.latest_macos_release()


if __name__ == "__main__":
    unittest.main()
