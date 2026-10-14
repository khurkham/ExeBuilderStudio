"""Stable application entry point.

Keep this file at the repository root for existing launch scripts and packagers.
"""
import os
import sys

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from app.ui.main_window import Window
from app.ui.theme import APP_STYLESHEET
from ui_assets import FONT_ERRORS, load_fonts, resource


def main():
    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Khurkham.ExeBuilderStudio"
        )

    app = QApplication(sys.argv)
    load_fonts()
    if FONT_ERRORS:
        QMessageBox.warning(None, "Embedded fonts", "\n".join(FONT_ERRORS))

    app.setStyleSheet(APP_STYLESHEET)
    # Use the native macOS icon when packaged for macOS; keep ICO on Windows.
    icon_name = "app.icns" if sys.platform == "darwin" and resource("app.icns").is_file() else "app.ico"
    app.setWindowIcon(QIcon(str(resource(icon_name))))
    window = Window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
