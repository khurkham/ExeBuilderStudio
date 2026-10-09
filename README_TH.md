# EXE Builder Studio 1.0
รุ่นปรับปรุงเพิ่ม SignTool และใบรับรองอัตโนมัติ: อ่าน README_SIGNING_TH.md
โปรเจกต์ Python Desktop สำหรับ Windows 10/11 เปิดแก้ด้วย IntelliJ IDEA ได้
มีเมนู English / ไทย / တႆး และฝังฟอนต์ TH Sarabun New กับ A J Kunheing E-T-M 05 ที่แนบมา

## เริ่มใช้งาน
1. ติดตั้ง Python 3.11 หรือ 3.12 แบบ 64-bit จาก https://www.python.org/downloads/windows/
2. แตก ZIP แล้วเปิด Start.bat ครั้งแรกต้องต่ออินเทอร์เน็ตเพื่อติดตั้ง dependencies
3. IntelliJ IDEA: เปิดโฟลเดอร์โปรเจกต์ ตั้ง Python interpreter เป็น .venv\Scripts\python.exe แล้วเปิด main.py (ต้องมี Python plugin ที่รองรับในรุ่น IDE ของคุณ)

## เครื่องมือ: ดาวน์โหลดภายในโปรแกรม
อ่าน UPDATE_DOWNLOADS_TH.md สำหรับรุ่นนี้
เครื่องมือแต่ละตัวมีปุ่ม ตรวจสอบโปรแกรม / ดาวน์โหลด / อัปเดต / ติดตั้งไฟล์ที่ดาวน์โหลด
- ตรวจสอบ: ตรวจตำแหน่งและเวอร์ชัน หากไม่พบจะแสดง “กรุณาดาวน์โหลดโปรแกรม”
- ดาวน์โหลด: ดึงไฟล์จากแหล่งทางการ พร้อมแถบความคืบหน้า ไม่เปิดเว็บเบราว์เซอร์
- ติดตั้ง: ใช้ไฟล์ที่ดาวน์โหลดไว้ Java และ Launch4j แตก ZIP ลงโฟลเดอร์เครื่องมือของแอป ส่วน Inno Setup, Python และ SDK เปิดหน้าติดตั้งของผู้ผลิต
- อัปเดต: ตรวจรุ่นล่าสุด ดาวน์โหลด และเปิดการติดตั้งเมื่อมีรุ่นใหม่ หลังติดตั้งจะตรวจเครื่องมืออีกครั้ง
- PyInstaller: ดาวน์โหลดแพ็กเกจสำหรับ Python ที่เลือก แล้วติดตั้งจากแพ็กเกจนั้น ไม่ติดตั้ง dependencies ของโปรเจกต์เป้าหมายให้
เลือก Java รุ่นหลักให้ตรงกับโปรเจกต์ ปุ่มอัปเดต Java อัปเดตภายในรุ่นหลักที่เลือก
โฟลเดอร์ดาวน์โหลด: %LOCALAPPDATA%\ExeBuilderStudio\downloads
โฟลเดอร์เครื่องมือแบบ ZIP: %LOCALAPPDATA%\ExeBuilderStudio\tools

## Java JAR → EXE
เลือก executable JAR ที่มี Main-Class ใน manifest แล้วเลือกโฟลเดอร์ผลลัพธ์ ชื่อภาษาอังกฤษ และ ICO (ไม่บังคับ)
ตั้ง Java ขั้นต่ำให้ตรงกับรุ่นที่ใช้ compile เช่น 17, 21, 25; ไม่ควรใช้ค่า 1.8.0 กับโปรแกรมที่ compile ด้วย Java รุ่นใหม่
เลือกโฟลเดอร์ Java ที่มี bin\java.exe หากต้องการรวม runtime ไปด้วย คัดลอกทั้ง runtime และตรวจสอบสิทธิ์การแจกจ่ายของ distribution นั้น
โปรแกรมสร้าง launch4j.xml และ EXE ที่ฝัง JAR อยู่ภายใน (dontWrapJar=false)
หากมี lib อยู่ข้าง JAR จะคัดลอกไปด้วย Dependencies นอก lib หรือข้อมูล/รูป/เสียงต้องคัดลอกเองเข้าโฟลเดอร์ release
JAR ที่ไม่มี Main-Class ต้องแก้ manifest หรือสร้าง executable JAR ก่อนใช้งาน
เมื่อรวม Java ให้แจกทั้งโฟลเดอร์ release หรือใช้ Inno Setup ไม่ใช่เฉพาะ EXE
ไม่รวม runtime: เครื่องปลายทางต้องมี Java ที่รองรับ
ไม่รับรอง Windows XP/7 สำหรับเครื่องมือและ runtime รุ่นปัจจุบัน

## Python → EXE
เลือกไฟล์ entry point เช่น main.py แล้วเลือก python.exe ที่รันโปรเจกต์นั้นได้
เลือก Onefile สำหรับ EXE เดียว หรือยกเลิกเพื่อส่งออกแบบ Onedir (เหมาะกับโปรแกรมใหญ่)
เลือก Show console หากเป็นโปรแกรม command line
โฟลเดอร์ข้อมูลเพิ่มเติมจะถูกใส่ใน bundle ด้วยชื่อโฟลเดอร์เดิม เช่น assets → assets
ใส่ hidden imports คั่นด้วย comma เมื่อโปรแกรมโหลดโมดูลแบบ dynamic
ผลลัพธ์อยู่ output\dist; หากเป็น Onedir ต้องแจกโฟลเดอร์ทั้งหมด
ทรัพยากรใน bundle ต้องถูกอ้างอิงจาก __file__ หรือ sys._MEIPASS ตามวิธีของ PyInstaller ไม่ควรเขียนข้อมูลถาวรกลับเข้า bundle
ทดสอบบน Windows ที่ไม่มี Python ก่อนแจกจริง

## ตัวติดตั้ง Inno Setup
เลือกโฟลเดอร์ release ที่มีเฉพาะไฟล์พร้อมแจก อย่าเลือกทั้งโฟลเดอร์ source code หรือ virtual environment
ระบุชื่อ EXE ในโฟลเดอร์ รุ่น 1.0 ผู้พัฒนา และโฟลเดอร์ผลลัพธ์ที่อยู่นอก release
ได้ไฟล์ .iss และ AppName_Setup.exe รองรับ shortcut Start Menu และ desktop แบบเลือกได้
ติดตั้งระดับผู้ใช้ใน LOCALAPPDATA\Programs โดยไม่ต้องบังคับสิทธิ์ admin
ชื่อโปรแกรมและผู้พัฒนาเดิมทำให้ AppId เดิมสำหรับอัปเดตเวอร์ชัน
ไอคอน shortcut ใช้ไอคอนที่ฝังใน EXE; ICO ในแท็บ installer ใช้สำหรับตัว Setup

## Logo → ICO
รองรับ PNG/JPG/JPEG/BMP/WebP/ICO คงสัดส่วนภาพ ไม่ตัดขอบ เติมพื้นที่โปร่งใสเป็นสี่เหลี่ยม
ICO รวม 16, 24, 32, 48, 64, 128, 256 px; JPG ไม่มี alpha ดั้งเดิมจึงไม่สามารถลบพื้นหลังให้อัตโนมัติ

## สร้าง EXE ของ EXE Builder Studio เอง
เปิด PowerShell ในโฟลเดอร์ แล้วรัน:
  powershell -ExecutionPolicy Bypass -File .\Build_Studio.ps1
ได้ dist\ExeBuilderStudio\ExeBuilderStudio.exe แล้วใช้แท็บตัวติดตั้งเลือกโฟลเดอร์นี้เพื่อสร้าง ExeBuilderStudio_Setup.exe
ต้องสร้างบน Windows ไม่สามารถใช้ build ใน Linux นี้แทนไฟล์ Windows ที่ผ่านการทดสอบจริงได้
โปรแกรมมี Log ผลคำสั่ง ปุ่ม Stop และเปิดโฟลเดอร์ผลลัพธ์
Stop อาจเหลือไฟล์ชั่วคราว ควรเลือก output ใหม่ก่อนลองอีกครั้ง
ภาษาไทใหญ่ใช้ Unicode; หากข้อความต้นฉบับเป็น legacy encoding ต้องแปลง encoding ก่อน ไม่สามารถแก้เครื่องหมาย ???? ที่สูญเสียข้อมูลไปแล้วด้วยฟอนต์อย่างเดียว

## โครงสร้าง
main.py = UI, language, QProcess, settings
backend.py = validation, Launch4j XML, Inno script, ICO conversion
assets/fonts = ฟอนต์ที่แนบมา
requirements.txt / Start.bat / Build_Studio.ps1

## ขอบเขตการตรวจสอบ
ตรวจ syntax Python และทดสอบ backend ด้วยข้อมูลตัวอย่างในสภาพแวดล้อม Linux
ยังไม่ได้ทดสอบ UI หรือ compile EXE ด้วย Launch4j/PyInstaller/Inno Setup บน Windows
อ้างอิง:
https://launch4j.sourceforge.net/docs.html
https://pyinstaller.org/en/stable/usage.html
https://jrsoftware.org/ishelp/
