"""UI labels for English, Thai, and Shan."""

T = {
    # Application title
    'title': (
        'EXE Builder Studio',
        'โปรแกรมสร้าง EXE',
        'ပရူဝ်ႇၵရႅမ်ႇသၢင်ႈ EXE',
    ),

    # Windows build tabs
    'win_java': (
        'Java JAR → Setup Windows',
        'Java JAR → Setup Windows',
        'Java JAR → Setup Windows',
    ),
    'win_python': (
        'Python → Setup Windows',
        'Python → Setup Windows',
        'Python → Setup Windows',
    ),

    # macOS build tabs
    'mac_java': (
        'Java JAR → Setup macOS',
        'Java JAR → Setup macOS',
        'Java JAR → Setup macOS',
    ),
    'mac_python': (
        'Python → Setup macOS',
        'Python → Setup macOS',
        'Python → Setup macOS',
    ),

    # Windows build actions and descriptions
    'buildwin': (
        'Build Setup.exe',
        'สร้าง Setup.exe',
        'သၢင်ႈ Setup.exe',
    ),
    'win_java_note': (
        'Builds *_Setup.exe on Windows using JDK 17+ '
        '(jpackage app-image) and Inno Setup. '
        'PowerShell and WiX are not required.',
        'สร้าง *_Setup.exe บน Windows ด้วย JDK 17+ '
        '(jpackage app-image) และ Inno Setup '
        'ไม่ต้องใช้ PowerShell หรือ WiX Toolset',
        'သၢင်ႈ *_Setup.exe ၼိူဝ် Windows လူၺ်ႈ JDK 17+ '
        '(jpackage app-image) လႄႈ Inno Setup။ '
        'ဢမ်ႇလူဝ်ႇ PowerShell ဢမ်ႇၼၼ် WiX။',
    ),
    'win_python_note': (
        'Builds *_Setup.exe on Windows using Python, '
        'PyInstaller, and Inno Setup 6/7. '
        'PowerShell is not required. Install PyInstaller '
        'in the selected Python environment first.',
        'สร้าง *_Setup.exe บน Windows ด้วย Python, '
        'PyInstaller และ Inno Setup 6/7 ไม่ต้องใช้ PowerShell '
        'ต้องติดตั้ง PyInstaller ใน Python ที่เลือกก่อน',
        'သၢင်ႈ *_Setup.exe ၼိူဝ် Windows လူၺ်ႈ Python, '
        'PyInstaller လႄႈ Inno Setup 6/7။ '
        'ဢမ်ႇလူဝ်ႇ PowerShell။ '
        'ဢိၼ်ႇသတေႃး PyInstaller ၼႂ်း Python ဢၼ်လိူၵ်ႈဝႆႉ။',
    ),

    # macOS build actions and descriptions
    'buildmac': (
        'Build Setup.dmg',
        'สร้าง Setup.dmg',
        'သၢင်ႈ Setup.dmg',
    ),
    'mac_java_source': (
        'Java JAR file',
        'ไฟล์ Java JAR',
        'ၾၢႆႇ Java JAR',
    ),
    'mac_python_source': (
        'Python project folder or .py file',
        'โฟลเดอร์โปรเจกต์ Python หรือไฟล์ .py',
        'ၾူဝ်ႇလ်ႇတိူဝ်ႇ Python ဢမ်ႇၼၼ်ၾၢႆႇ .py',
    ),
    'mac_java_note': (
        'Builds *_Setup.dmg directly on macOS. '
        'Requires a full JDK 17+ with jpackage.',
        'สร้าง *_Setup.dmg โดยตรงบน macOS '
        'ต้องมี JDK 17+ ที่มี jpackage',
        'သၢင်ႈ *_Setup.dmg တူၵ်းၼိူဝ် macOS။ '
        'လူဝ်ႇမီး JDK 17+ ဢၼ်မီး jpackage။',
    ),
    'mac_python_note': (
        'Builds *_Setup.dmg directly on macOS. '
        'Requires Python 3; PyInstaller is installed '
        'in an isolated environment. Check requirements.txt '
        'for Windows-only packages.',
        'สร้าง *_Setup.dmg โดยตรงบน macOS ต้องมี Python 3 '
        'โดยติดตั้ง PyInstaller ในสภาพแวดล้อมแยก '
        'ควรตรวจ requirements.txt ว่ามีแพ็กเกจเฉพาะ Windows หรือไม่',
        'သၢင်ႈ *_Setup.dmg တူၵ်းၼိူဝ် macOS။ '
        'လူဝ်ႇ Python 3၊ PyInstaller တေဢိၼ်ႇသတေႃးၼႂ်း environment '
        'ထုၵ်ႇလီၸႅတ်ႈ requirements.txt တႃႇ package Windows။',
    ),

    # Common interface labels
    'installer': (
        'Installer',
        'ตัวติดตั้ง',
        'တူဝ်ဢိၼ်ႇသတေႃး',
    ),
    'icon': (
        'Logo → ICO / ICNS',
        'โลโก้ → ICO / ICNS',
        'လူဝ်ႇၵူဝ်ႇ → ICO / ICNS',
    ),
    'win_tools': ('Windows Tools / Java', 'เครื่องมือ Windows / Java', 'Windows ၶိူင်ႈမိုဝ်း / Java'),
    'mac_tools': ('macOS Tools / Java', 'เครื่องมือ macOS / Java', 'macOS ၶိူင်ႈမိုဝ်း / Java'),
    'tools': (
        'Tools / Java',
        'เครื่องมือ / Java',
        'ၶိူင်ႈမိုဝ်း / Java',
    ),

    'win_tools': (
        'Windows Tools / Java',
        'เครื่องมือ Windows / Java',
        'ၶိူင်ႈမိုဝ်း Windows / Java',
    ),
    'mac_tools': (
        'macOS Tools / Java',
        'เครื่องมือ macOS / Java',
        'ၶိူင်ႈမိုဝ်း macOS / Java',
    ),
    'browse': (
        'Browse',
        'เลือกไฟล์',
        'လိူၵ်ႈၾၢႆႇ',
    ),
    'source': (
        'Source file',
        'ไฟล์ต้นฉบับ',
        'ၾၢႆႇတူၼ်ႈတေႃ',
    ),
    'python_source': (
        'Python file or project folder',
        'ไฟล์ Python หรือโฟลเดอร์โปรเจกต์',
        'ၾၢႆႇ Python ဢမ်ႇၼၼ် ၾူဝ်ႇလ်ႇတိူဝ်ႇပရူဝ်ႇၵျႅတ်ႉ',
    ),
    'output': (
        'Output folder',
        'โฟลเดอร์ผลลัพธ์',
        'ၾူဝ်ႇလ်ႇတိူဝ်ႇဢွၵ်ႇ',
    ),
    'name': (
        'App name (English)',
        'ชื่อโปรแกรม (อังกฤษ)',
        'ၸိုဝ်ႈပရူဝ်ႇၵရႅမ်ႇ (ဢင်းၵိတ်ႉ)',
    ),
    'version': (
        'Version',
        'เวอร์ชัน',
        'ဝႃးသျိၼ်း',
    ),
    'publisher': (
        'Publisher',
        'ผู้พัฒนา',
        'ၽူႈၶူင်သၢင်ႈ',
    ),
    'minimum': (
        'Minimum Java version',
        'Java ขั้นต่ำ',
        'Java ဝႃးသျိၼ်းတႅမ်ႇသုတ်း',
    ),
    'data': (
        'Extra data folder (optional)',
        'โฟลเดอร์ข้อมูลเพิ่มเติม (ไม่บังคับ)',
        'ၾူဝ်ႇလ်ႇတိူဝ်ႇၶေႃႈမုၼ်း (လိူၵ်ႈလႆႈ)',
    ),
    'hidden': (
        'Hidden imports (comma-separated)',
        'Hidden imports (คั่นด้วยจุลภาค)',
        'Hidden imports (ၶႅၼ်ႈလူၺ်ႈၵွမ်ႇမႃႇ)',
    ),
    'folder': (
        'Release folder to install',
        'โฟลเดอร์โปรแกรมที่จะติดตั้ง',
        'ၾူဝ်ႇလ်ႇတိူဝ်ႇပရူဝ်ႇၵရႅမ်ႇ',
    ),
    'exe': (
        'EXE filename in release folder',
        'ชื่อไฟล์ EXE ในโฟลเดอร์',
        'ၸိုဝ်ႈၾၢႆႇ EXE',
    ),

    # Installer and icon actions
    'makeinstaller': (
        'Build installer',
        'สร้างตัวติดตั้ง',
        'သၢင်ႈတူဝ်ဢိၼ်ႇသတေႃး',
    ),
    'convert': (
        'Convert icon',
        'แปลงไอคอน',
        'ပိၼ်ႇ icon',
    ),

    # Java and Python tools
    'check': (
        'Check Java',
        'ตรวจ Java',
        'ၸႅတ်ႈထတ်း Java',
    ),
    'installjava': (
        'Download / install Java',
        'ดาวน์โหลด / ติดตั้ง Java',
        'လူတ်ႇ / ဢိၼ်ႇသတေႃး Java',
    ),
    'runinstaller': (
        'Run downloaded installer',
        'เปิดไฟล์ติดตั้งที่ดาวน์โหลดแล้ว',
        'ပိုတ်ႇၾၢႆႇဢိၼ်ႇသတေႃး',
    ),
    'installpython': (
        'Install PyInstaller in selected Python',
        'ติดตั้ง PyInstaller ใน Python ที่เลือก',
        'ဢိၼ်ႇသတေႃး PyInstaller ၼႂ်း Python',
    ),
    'save': (
        'Save tool settings',
        'บันทึกเครื่องมือ',
        'သိမ်းၶိူင်ႈမိုဝ်း',
    ),

    # Build controls and status
    'stop': (
        'Stop',
        'หยุด',
        'ၵိုတ်း',
    ),
    'open': (
        'Open output folder',
        'เปิดโฟลเดอร์ผลลัพธ์',
        'ပိုတ်ႇၾူဝ်ႇလ်ႇတိူဝ်ႇဢွၵ်ႇ',
    ),
    'ready': (
        'Ready • Build on Windows',
        'พร้อมใช้งาน • สร้าง EXE บน Windows',
        'တူဝ်ႈတၼ်း • သၢင်ႈ EXE ၼိူဝ် Windows',
    ),
}