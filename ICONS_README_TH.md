รุ่น 1.0.2
แตก ZIP ในโฟลเดอร์ใหม่ เปิด Run_This_Version.bat
ต้องเห็นโลโก้บนซ้าย รุ่น 1.0.2 และแท็บเกี่ยวกับ
โลโก้ PNG: logo.png และ assets/logo.png
ไอคอน ICO: ExeBuilderStudio.ico และ assets/app.ico
ตั้ง AppUserModelID ก่อนสร้าง QApplication บน Windows และตั้งไอคอนทั้งแอปและหน้าต่าง
ไฟล์ EXE ต้องสร้างใหม่: powershell -ExecutionPolicy Bypass -File .\Build_Studio.ps1
เปิด dist/ExeBuilderStudio/ExeBuilderStudio.exe
หากปักหมุด Taskbar ของ EXE เก่าไว้ ให้ถอนหมุด แล้วปักหมุด EXE ใหม่
หากเปิดผ่าน IntelliJ IDEA หรือ Python ไอคอนการจัดกลุ่มอาจต่างจาก EXE ที่สร้างแล้ว
ตรวจโค้ดใน ZIP และตรวจ ICO หลายขนาดแล้ว ยังไม่ได้ทดสอบ Windows Taskbar จริง
