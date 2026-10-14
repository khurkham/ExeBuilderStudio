"""Regression checks for ASCII progress percentages in the UI source."""
from pathlib import Path
import unittest


class ProgressAsciiDigitsTests(unittest.TestCase):
    def test_progress_bar_does_not_use_qt_localized_percent_text(self):
        source = (Path(__file__).resolve().parents[1] / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.build_progress.setFormat('')", source)
        self.assertIn("{self.build_progress.value()}% (estimated)", source)
        self.assertNotIn("self.build_progress.setFormat('%p%')", source)


if __name__ == "__main__":
    unittest.main()
