"""Embedded assets resolved identically in Python, PyInstaller onedir and onefile."""
import sys
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase
BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
FAMILIES={}
FONT_ERRORS=[]
def resource(name):return BASE/'assets'/name

def load_fonts():
    for key,name in [('th','thai.ttf'),('shn','shan.ttf')]:
        path=resource('fonts/'+name)
        font_id=QFontDatabase.addApplicationFont(str(path))
        families=QFontDatabase.applicationFontFamilies(font_id) if font_id>=0 else []
        if not families:FONT_ERRORS.append(f'Cannot load bundled font: {path}')
        else:FAMILIES[key]=families[0]

def apply_font(window,language):
    families=[FAMILIES.get('shn',''),FAMILIES.get('th',''),'Segoe UI'] if language==2 else [FAMILIES.get('th',''),FAMILIES.get('shn',''),'Segoe UI'] if language==1 else ['Segoe UI',FAMILIES.get('th',''),FAMILIES.get('shn','')]
    font=QFont(); font.setFamilies([x for x in families if x]);font.setPointSize([12,19,15][language])
    from PySide6.QtWidgets import QApplication,QWidget
    QApplication.instance().setFont(font);window.setFont(font)
    for widget in window.findChildren(QWidget):widget.setFont(font)
    # Language selector always has both scripts available.
    selector=QFont(font);selector.setFamilies([FAMILIES.get('shn',''),FAMILIES.get('th',''),'Segoe UI']);window.lang.setFont(selector)
