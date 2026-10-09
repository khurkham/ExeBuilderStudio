# ExeBuilderStudio 1.0.0 — Windows + macOS รุ่นทดลอง

ผู้พัฒนา Khurkham Langkhur

Windows: ติดตั้ง ExeBuilderStudio_Setup.exe หน้า Java/Python/Installer เดิมใช้งานเหมือนเดิม
macOS: เลือก DMG ตรงกับเครื่อง Apple Silicon หรือ Intel เปิด DMG และลาก ExeBuilderStudio.app ไป Applications
รุ่นนี้ไม่ได้ลงลายเซ็น Developer ID หรือ notarization ของ Apple จึงอาจถูก Gatekeeper ปฏิเสธ ให้ทดลองเฉพาะไฟล์ที่คุณตรวจสอบและเชื่อถือ ไม่ต้องปิดระบบป้องกันทั้งเครื่อง

## Python → APP บน Mac
เปิดแท็บ macOS APP / DMG เลือก Python interpreter จริง เช่น /path/to/project/.venv/bin/python (ไม่ใช่ตัว ExeBuilderStudio.app)
ติดตั้ง requirements ของโปรเจกต์และ PyInstaller ใน Python ตัวเดียวกันก่อนสร้าง
เลือก main.py, Output folder, ชื่อแอปภาษาอังกฤษ, Bundle ID เช่น com.khurkham.myapp
เลือกไอคอน .icns และโฟลเดอร์ assets หากมี
Architecture เริ่มด้วย native ซึ่งใช้สถาปัตยกรรมของ Python ที่เลือก arm64/x86_64/universal2 ต้องมี Python และไลบรารีรองรับทั้งหมด มิฉะนั้น PyInstaller จะปฏิเสธ
Apple signing identity เป็นตัวเลือกสำหรับใบรับรองที่มีอยู่ใน Keychain ไม่ได้สร้างใบรับรอง Apple ทดสอบให้
กด Python → APP ได้ output/dist/ชื่อ.app ใช้ onedir/windowed และนำ assets ไปกับแอป
ต้องทดสอบโค้ดโปรเจกต์ที่ใช้พาธหรือคำสั่งเฉพาะ Windows ให้รองรับ Mac เอง

## Java → APP บน Mac
เลือก jpackage จาก JDK บน Mac, โฟลเดอร์ที่รวม JAR และไลบรารีทั้งหมด, ชื่อ JAR เฉพาะชื่อไฟล์
ใช้ชื่อแอป Bundle ID เวอร์ชันและไอคอนจากช่องด้านบนร่วมกัน
Main class เว้นว่างได้หาก JAR มี Main-Class ใน manifest
Java folder เว้นว่างเพื่อให้ jpackage รวม runtime อัตโนมัติ หรือเลือก runtime Mac ที่มี bin/java
รุ่นทดลองสร้าง Java APP ยังไม่รองรับลงลายเซ็น Apple อัตโนมัติ ช่อง Apple signing identity ต้องว่าง

## APP → DMG
เลือก .app ที่สร้างแล้ว (หรือแอปอื่นที่มีโครงสร้างถูกต้อง) และ Output folder ที่อยู่นอก .app
กด APP → DMG จะได้ชื่อ.dmg ภายในมี APP และทางลัด Applications
สามารถเลือกโฟลเดอร์ผลลัพธ์เดียวกับ APP ได้ เพราะโปรแกรมจัด staging เฉพาะ APP ไม่รวม work/spec

## โลโก้
เลือกภาพในช่อง logo แล้วกด Convert logo → ICNS ได้ชื่อ.icns ใน Output folder
ตัวแปลง ICO เดิมยังใช้บน Windows ได้

## เครื่องมือและข้อจำกัด
Check Mac tools แสดงตำแหน่งเครื่องมือและตรวจ PyInstaller ใน Python ที่เลือก
บน Mac ปิดหน้าที่ใช้ Windows; ระบบดาวน์โหลดอัปเดต Windows ถูกปิด เพื่อไม่ให้รับ EXE ผิดระบบ
รุ่นนี้ยังไม่มีตัวดาวน์โหลดเครื่องมือ Mac, notarization, การอัปเดต Mac อัตโนมัติ หรือการสั่งสร้างโปรเจกต์ Mac จากหน้า Windows ผ่าน cloud
แถบสร้างเป็นแถบกำลังทำงาน ไม่ใช่เปอร์เซ็นต์ประมาณที่ไม่มีข้อมูลจริง และดูขั้นตอนจาก Log ได้
Windows สร้าง EXE/Setup บน Windows; Mac สร้าง APP/DMG บน Mac

## สร้างตัว ExeBuilderStudio บน Mac จากโค้ด
เปิด Terminal ในโฟลเดอร์โปรเจกต์ แล้วรัน:

bash Build_Studio_Mac.sh

ผลลัพธ์ mac_dist/ExeBuilderStudio.app และ mac_installer/ExeBuilderStudio.dmg
GitHub Actions cross-platform-trial.yml สร้าง Windows และ Mac 2 สถาปัตยกรรมและทดสอบจริงก่อนเผยแพร่ prerelease แยกจาก stable
