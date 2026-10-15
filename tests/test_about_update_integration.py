"""Regression checks: the universal updater must not replace original About content."""
from pathlib import Path
import unittest


class AboutIntegrationTests(unittest.TestCase):
    def test_original_about_cards_remain_and_universal_card_is_appended(self):
        source = (Path(__file__).parents[1] / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.mac_update_card=MacUpdateCard(); box.addWidget(self.mac_update_card)", source)
        self.assertIn("add_about_updater(self,box)", source)
        self.assertIn("self.universal_update_card=UniversalUpdateCard(); box.addWidget(self.universal_update_card)", source)
        self.assertIn("self.universal_update_card.set_language(i)", source)


if __name__ == "__main__":
    unittest.main()
