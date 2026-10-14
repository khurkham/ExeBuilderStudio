# EXE Builder Studio 1.2

โปรแกรม Desktop สำหรับสร้างตัวติดตั้ง Windows และ macOS รองรับเมนู English / ไทย / တႆး

## หลักการสร้างตัวติดตั้ง: สร้างบนเครื่องเป้าหมายเท่านั้น ไม่มี Cloud Build

โปรแกรมจะสร้างตัวติดตั้งเฉพาะบนระบบปฏิบัติการที่ตรงกับเป้าหมายเท่านั้น **ไม่มีการอัปโหลดโปรเจกต์ไปยัง Cloud Build และไม่ต้องใช้ GitHub Repository หรือ Token**

| เมนู | ระบบที่สร้างได้ | เครื่องมือหลัก | ผลลัพธ์ |
|---|---|---|---|
| Java JAR → Setup Windows | Windows เท่านั้น | JDK 17+ ที่มี `jpackage` และ Inno Setup 6/7 (ไม่ต้องใช้ WiX หรือ PowerShell) | `*_Setup.exe` |
| Python → Setup Windows | Windows เท่านั้น | Python 3, PyInstaller และ Inno Setup 6/7 | `*_Setup.exe` |
| Java JAR → Setup macOS | Mac เท่านั้น | JDK 17+ ที่มี `jpackage` | `*_Setup.dmg` |
| Python → Setup macOS | Mac เท่านั้น | Python 3, PyInstaller และ `create-dmg` (ถ้าติดตั้งไว้) หรือ `hdiutil` ที่มากับ macOS | `*_Setup.dmg` |

หากเปิดโปรแกรมบน Mac แล้วกดสร้าง `.exe` โปรแกรมจะแสดงหน้าต่างเตือนให้ไปสร้างบนเครื่อง Windows และหยุดการ Build หากเปิดบน Windows แล้วกดสร้าง `.dmg` โปรแกรมจะแสดงหน้าต่างเตือนให้ไปสร้างบนเครื่อง Mac และหยุดการ Build ก่อนเริ่มแพ็กเกจ

เลือกไฟล์ JAR หรือไฟล์/โฟลเดอร์โปรเจกต์ Python, Output folder, ชื่อแอป และโลโก้ได้จากแท็บ Build ที่ตรงกับเป้าหมาย โปรเจกต์ Python จะถูกแพ็กเกจแบบโฟลเดอร์ แล้วนำไปสร้างเป็นตัวติดตั้งขั้นสุดท้าย หากมีไฟล์ Setup ชื่อเดียวกัน โปรแกรมจะถามก่อนเขียนทับ และจะแทนที่ไฟล์เดิมเมื่อ Build ใหม่สำเร็จเท่านั้น

### เลือกเวอร์ชัน JDK สำหรับ Build

ในแท็บ **Tools / Java** ใช้ช่อง **JDK ที่ใช้สร้างตัวติดตั้ง Java** เพื่อเลือก JDK ที่ติดตั้งอยู่ (เช่น 17, 21 หรือ 25) ได้โดยตรง กด **ค้นหา JDK อีกครั้ง** เพื่อสแกนเครื่อง หรือ **เลือกโฟลเดอร์ JDK…** เพื่อระบุโฟลเดอร์เอง ต้องเลือกโฟลเดอร์รากของ Full JDK ที่มี `bin/jpackage.exe` บน Windows หรือ `bin/jpackage` บน Mac และต้องเป็น JDK 17 ขึ้นไป หากเลือก Auto-detect โปรแกรมจะค้นหา JDK ให้เอง

### หากขึ้นข้อความว่าไม่พบ JDK หรือ jpackage

การเห็น `java version 25.0.3` ไม่ได้ยืนยันว่ามี JDK ครบชุด เพราะ `java.exe` ใน `Common Files\Oracle\Java\javapath` อาจเป็นเพียงตัวเรียก Java Runtime โปรแกรมเวอร์ชันนี้จะค้นหา JDK ในตำแหน่งติดตั้งที่พบบ่อยให้อัตโนมัติ หากยังไม่พบ `jpackage.exe` ให้ติดตั้ง **Full JDK 17 หรือใหม่กว่า** (เช่น Temurin JDK) และตั้ง `JAVA_HOME` ให้ชี้ไปยังโฟลเดอร์รากของ JDK เช่น `C:\Program Files\Eclipse Adoptium\jdk-21...` ไม่ใช่โฟลเดอร์ `bin` และไม่ใช่ `javapath` จากนั้นเปิดโปรแกรมใหม่

โปรแกรมกรองโฟลเดอร์พัฒนา เช่น `.venv`, `venv`, `.idea`, `.git`, `tests`, cache, `build` และ `dist` ออกจากแพ็กเกจ Python รวมทั้งไฟล์ลับ เช่น `.env*`, private key, `.pfx` และ `.p12`

## เริ่มใช้งานบน Windows

1. ติดตั้ง Python 3.11 หรือ 3.12 แบบ 64-bit จาก https://www.python.org/downloads/windows/
2. แตก ZIP แล้วเปิด `Start.bat` โปรแกรมจะสร้าง environment และติดตั้ง dependencies ตาม `requirements.txt`
3. หากพัฒนาด้วย IntelliJ IDEA ให้เลือก Python interpreter เป็น `.venv\Scripts\python.exe`

## Build ตัวโปรแกรม ExeBuilderStudio เอง

บน Windows เปิด PowerShell ในโฟลเดอร์โปรเจกต์ แล้วรัน:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Build_Studio.ps1 -CreateInstaller
```

ต้องมี Python และ Inno Setup บนเครื่องที่ใช้ Build โปรแกรมจะสร้าง `ExeBuilderStudio_Setup.exe` ในโฟลเดอร์ `installer_output`

## สร้างแอป ExeBuilderStudio สำหรับแจกจ่ายบน macOS

บนเครื่อง Mac ให้ติดตั้ง Python 3.11 หรือ 3.12 สำหรับขั้นตอนสร้างแพ็กเกจ แล้วรัน:

```bash
bash macos/build_macos_distribution.sh
```

สคริปต์จะใช้ PyInstaller สร้าง `ExeBuilderStudio.app` พร้อม Python runtime, PySide6, Pillow, ฟอนต์และ assets ที่แอปต้องใช้ แล้วสร้างไฟล์ `.dmg` ใน `macos_release/` ตามสถาปัตยกรรมของ Mac ที่ใช้ Build (Apple Silicon หรือ Intel) หากติดตั้ง `create-dmg` ไว้ จะได้หน้าต่าง DMG ที่จัดตำแหน่งไอคอนแอปและทางลัด Applications ให้ หากไม่ได้ติดตั้ง สคริปต์จะใช้ `hdiutil` ที่มากับ macOS แทน สามารถติดตั้งแบบเลือกได้ด้วย `brew install create-dmg` หากต้องการรวม JDK 17+ ที่มีสิทธิ์แจกจ่ายและตรงกับสถาปัตยกรรม ให้กำหนด `EBS_BUNDLE_JDK_HOME` ก่อนรันสคริปต์ ดูรายละเอียดใน `macos/README_TH.md`

ข้อสำคัญ: การ Bundle แอป ExeBuilderStudio ไม่ได้ Bundle toolchain สำหรับทุกโปรเจกต์ของผู้ใช้โดยอัตโนมัติ การสร้าง Java JAR ต้องใช้ JDK 17+ ที่มี `jpackage` (เว้นแต่ Bundle ไว้) ส่วนการสร้าง Python project ยังต้องมี Python 3 บน Mac และอาจต้องใช้อินเทอร์เน็ตเพื่อติดตั้ง dependencies ของโปรเจกต์เป้าหมาย

## GitHub Releases และการอัปเดตในแอป macOS

ควรเผยแพร่ Windows และ macOS ด้วยเลขเวอร์ชันเดียวกันใน GitHub Release เดียวกัน โดย Windows ใช้ `ExeBuilderStudio_Setup.exe` ส่วนตัวอัปเดต macOS จะค้นหาไฟล์ DMG ที่มีชื่อระบุ `macOS` และสถาปัตยกรรมตรงกับเครื่อง เช่น `ExeBuilderStudio-1.1-macOS-arm64.dmg` หรือ `ExeBuilderStudio-1.1-macOS-x86_64.dmg`

บน macOS ให้เปิดแท็บ **About → Check for Updates** แอปจะตรวจสอบ GitHub Release รุ่นเสถียรล่าสุด ดาวน์โหลด DMG ผ่าน HTTPS และตรวจสอบ SHA-256 เทียบกับข้อมูลไฟล์ใน GitHub ก่อนเปิด DMG ให้ติดตั้ง เนื่องจาก Build ปัจจุบันยังไม่ได้ลงนามโค้ดและ Notarize จึงยังไม่สามารถแทนที่แอปที่กำลังเปิดอยู่โดยอัตโนมัติได้ ให้ปิด ExeBuilderStudio แล้วลากแอปใหม่ไปยัง Applications และเลือก Replace เมื่อระบบถาม

### ขั้นตอนเผยแพร่รุ่นใหม่

1. เปลี่ยน `APP_VERSION` และ `BUILD_REVISION` ใน `app/services/tool_downloads.py` แล้วทดสอบ Build Windows
2. เปิด GitHub Actions แล้วรัน **Windows installer release (manual only)** เพื่อเผยแพร่ Setup EXE และสร้าง GitHub Release ตามเวอร์ชันหากยังไม่มี
3. รัน **Temporary macOS DMG release (run once)** เพื่อ Build DMG บน macOS อัปโหลด DMG และไฟล์ SHA-256 ไปยัง Release เดียวกัน จากนั้น Workflow macOS จะลบตัวเองหลังเผยแพร่สำเร็จ
4. ตรวจสอบว่า Release เดียวกันมีไฟล์ติดตั้งทั้ง Windows และ macOS

Workflow ของ GitHub Actions ทำงานเมื่อสั่งด้วยตนเองเท่านั้น การ Push โค้ดไม่ทำให้เกิดการ Build อัตโนมัติ Workflow macOS ถูกออกแบบให้ใช้ชั่วคราวและลบตัวเองหลังเผยแพร่ ส่วน Workflow Windows ยังคงอยู่เพื่อใช้เผยแพร่ด้วยตนเอง โปรดตรวจสอบหน้า Billing ของบัญชี GitHub ก่อนใช้งาน เนื่องจากโควตาอาจขึ้นอยู่กับแผนและการตั้งค่าบัญชี

## การตรวจสอบ

ควรทดสอบการ Build จริงบนระบบปฏิบัติการเป้าหมายของแต่ละชนิด เนื่องจากเครื่องมือแพ็กเกจเป็นเครื่องมือเฉพาะระบบปฏิบัติการ dependencies เฉพาะโปรเจกต์หรือการโหลดทรัพยากรแบบไดนามิกอาจต้องปรับแต่งเพิ่มเติม

### แถบความคืบหน้าการสร้างตัวติดตั้ง

หน้าต่าง Build แสดงแถบความคืบหน้าแนวนอนและชื่อขั้นตอนที่กำลังทำงาน การสร้างตัวติดตั้งทำงานใน worker thread เพื่อให้หน้าต่างยังตอบสนองระหว่างรอ `jpackage`, PyInstaller หรือ Inno Setup เปอร์เซ็นต์เป็นค่าประมาณจากขั้นตอนและข้อความที่เครื่องมือรายงาน ไม่ใช่เปอร์เซ็นต์ที่เครื่องมือ Build รับรองอย่างแม่นยำ
