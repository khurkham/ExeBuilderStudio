"""Application entry point for ExeBuilderStudio."""
import sys, os
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from signing import detect_signtool
from ui_assets import resource, load_fonts, FONT_ERRORS
from app.window import Window


def main():
 if os.name=='nt':
  import ctypes
  ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Khurkham.ExeBuilderStudio')
 app=QApplication(sys.argv)
 load_fonts()
 if FONT_ERRORS:QMessageBox.warning(None,'Embedded fonts','\n'.join(FONT_ERRORS))
 app.setStyleSheet('QWidget {background:#101c30; color:#e7edf7;} QLineEdit,QPlainTextEdit,QComboBox {background:#192b45; border:1px solid #355074; border-radius:5px; padding:6px;} QPushButton {background:#235e8e; border-radius:5px; padding:9px;} QPushButton:hover {background:#317bb4;} QPushButton:disabled {color:#8292a8;} QTabBar::tab {padding:12px; margin-right:5px; border:1px solid #355074; border-top-left-radius:12px; border-top-right-radius:12px; background:#192b45;} QTabBar::tab:selected {background:#235e8e; border-bottom:3px solid #7dcfff;} QProgressBar {border:1px solid #355074; border-radius:5px; text-align:center; min-height:20px;} QProgressBar::chunk {background:#43b6dd;}')
 app.setWindowIcon(QIcon(str(resource('app.ico'))))
 w=Window(); w.show(); sys.exit(app.exec())


if __name__=='__main__':
 main()
