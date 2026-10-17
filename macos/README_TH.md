# แจกจ่าย ExeBuilderStudio บน macOS

สคริปต์ `build_macos_distribution.sh` สร้างแอป `.app` และไฟล์ `.dmg` แบบ Native บนเครื่อง Mac เท่านั้น ไม่มี Cloud Build หรือ GitHub Actions

## สิ่งที่สคริปต์รวมไว้ในแอป

- Python runtime และ dependencies ที่ PyInstaller เก็บจาก `requirements.txt` เช่น PySide6 และ Pillow
- ไฟล์ภาพและฟอนต์ใน `assets/`
- ไอคอน `.icns` ที่สร้างจาก `assets/logo.png`
- ไฟล์ checksum SHA-256 สำหรับ DMG

## สร้างไฟล์แจกจ่าย

1. แตกโปรเจกต์บน Mac
2. ติดตั้ง Python 3.11 หรือ 3.12 สำหรับใช้สร้างแพ็กเกจ
3. เปิด Terminal ในโฟลเดอร์โปรเจกต์ แล้วรัน:

   ```bash
   bash macos/build_macos_distribution.sh
   ```

4. ไฟล์ผลลัพธ์จะอยู่ใน `macos_release/` เช่น `ExeBuilderStudio-Standard-1.2-macOS-arm64.dmg` สำหรับ Apple Silicon หรือ `ExeBuilderStudio-Standard-1.2-macOS-x86_64.dmg` สำหรับ Intel Mac
5. ทดสอบเปิด `.app` จาก DMG บนเครื่อง Mac จริงก่อนแจกจ่าย

หากติดตั้ง `create-dmg` ไว้ สคริปต์จะใช้เครื่องมือนี้จัดหน้าต่าง DMG ให้มีตำแหน่งไอคอนแอปและทางลัด Applications หากไม่มี จะใช้ `hdiutil` ซึ่งติดมากับ macOS อยู่แล้ว จึงไม่บังคับให้ติดตั้ง Homebrew หรือเครื่องมือเสริม

ติดตั้ง `create-dmg` แบบเลือกได้ด้วย Homebrew:

```bash
brew install create-dmg
```

สคริปต์สร้างแอปตามสถาปัตยกรรมของ Mac ที่ใช้ Build จึงต้อง Build แยกบน Apple Silicon และ Intel หากต้องการแจกจ่ายทั้งสองสถาปัตยกรรม

## รวม JDK ไว้ในแอป (ตัวเลือก)

โดยปกติไม่รวม JDK เพื่อไม่ให้ไฟล์ใหญ่เกินไปและหลีกเลี่ยงการแจกจ่าย JDK ที่ไม่มีสิทธิ์เผยแพร่ หากมี Full JDK 17+ ที่ได้รับอนุญาตให้แจกจ่ายและตรงกับสถาปัตยกรรมของ Mac สามารถกำหนดตัวแปรก่อน Build ได้:

```bash
EBS_BUNDLE_JDK_HOME="/path/to/jdk" bash macos/build_macos_distribution.sh
```

JDK จะถูกคัดลอกไปไว้ใน `ExeBuilderStudio.app/Contents/Resources/tools/jdk` และตัวเลือก JDK ของแอปจะค้นพบตำแหน่งนี้อัตโนมัติ

## ข้อกำหนดของเครื่องมือ Build เป้าหมาย

- **Java JAR → DMG:** ต้องมี JDK 17+ ที่มี `jpackage` หากไม่ได้ Bundle JDK ไว้
- **Python project → DMG:** ต้องมี Python 3 บน Mac สำหรับสร้าง virtual environment และติดตั้ง PyInstaller รวมทั้ง dependencies ของโปรเจกต์ หาก `requirements.txt` ต้องดาวน์โหลดแพ็กเกจ จะต้องมีอินเทอร์เน็ตในขั้นตอน Build โปรเจกต์เป้าหมาย
- การ Bundle ตัว ExeBuilderStudio เองไม่ได้หมายความว่า toolchain สำหรับทุกโปรเจกต์ของผู้ใช้ถูก Bundle มาด้วยทั้งหมด

## หมายเหตุด้านความปลอดภัย

สคริปต์นี้ไม่ได้เซ็นแอปและไม่ได้ส่งแอปไป Notarize ตามข้อกำหนดของผู้ใช้ ดังนั้น macOS อาจแสดงคำเตือนเมื่อเปิดแอปที่ดาวน์โหลดจากอินเทอร์เน็ต


## ระบบตรวจสอบอัปเดต macOS
ในแท็บ About ของรุ่น macOS มีเมนู Check for Updates ซึ่งตรวจสอบ Stable Release จาก GitHub และเลือก DMG ตามสถาปัตยกรรมเครื่อง (arm64 หรือ x86_64) โดยดาวน์โหลดผ่าน HTTPS ตรวจ SHA-256 และตรวจโครงสร้าง DMG ก่อนเปิดให้ผู้ใช้ติดตั้งด้วยตนเอง

ตั้ง `APP_VERSION` และ `BUILD_REVISION` ใน `app/services/tool_downloads.py` ให้ตรงกับรุ่นที่กำลังเผยแพร่ทุกครั้ง และอัปโหลด DMG ของทั้งสองสถาปัตยกรรมใน Release เดียวกันหากต้องการรองรับ Mac ทั้งสองแบบ

ข้อจำกัด: ระบบปัจจุบันยังเปิด DMG ให้ผู้ใช้ติดตั้งเอง ไม่ได้แทนที่แอปเดิมโดยอัตโนมัติ ตัวติดตั้งที่แจกจ่ายสู่สาธารณะควรผ่าน Apple Developer ID Code Signing และ Notarization ก่อนเผยแพร่
