# ใบรับรองและ SignTool — EXE Builder Studio 1.0

## สิ่งที่เพิ่ม
- แท็บ **ใบรับรอง / ลงนาม** เลือก EXE, DLL หรือ MSI มาลงนามด้วย SignTool
- ตรวจหา SignTool ใน PATH และ Windows SDK เลือกเวอร์ชันล่าสุดที่ตรงกับเครื่อง
- ปุ่มดาวน์โหลด Windows SDK จาก Microsoft และปุ่มติดตั้งไฟล์ SDK ที่ดาวน์โหลดแล้ว
- รอ SDK installer จบ ตรวจพบ SignTool แล้วสร้างหรือใช้ใบรับรองทดสอบเดิม
- เมื่อเปิดโปรแกรมครั้งแรก และหลังติดตั้ง EXE Builder Studio ด้วยชุด Inno ที่ให้มา สร้างใบรับรองทดสอบอัตโนมัติ
- ใช้ใบรับรอง Code Signing ที่มีอยู่ใน CurrentUser\My หรือ LocalMachine\My ได้
- นำเข้าใบรับรอง PFX/P12 ด้วยรหัสผ่าน แล้วลงนามผ่าน thumbprint ใน Windows certificate store
- ตัวเลือก **ลงนาม EXE และ Setup หลังสร้าง** เริ่มต้นปิดไว้ เปิดเมื่อตั้งค่า SignTool และใบรับรองแล้ว
- SHA256 สำหรับลายเซ็น และ RFC 3161 timestamp URL แบบเลือกใส่ได้
- ปุ่มตรวจลายเซ็นและความเชื่อถือของ Windows แยกจากปุ่มลงนาม

## ติดตั้ง SignTool และสร้างใบรับรองอัตโนมัติ
1. เปิดแท็บ **ใบรับรอง / ลงนาม** กด **ดาวน์โหลด Windows SDK จาก Microsoft**
2. ดาวน์โหลด Windows SDK installer จาก Microsoft
3. กลับมากด **ติดตั้ง SDK → สร้างใบรับรอง** เลือกไฟล์ที่ดาวน์โหลด
4. อนุญาตหน้าต่าง UAC ของ Windows แล้วเลือก **Windows SDK Signing Tools for Desktop Apps** ในตัวติดตั้ง
5. เมื่อตัวติดตั้งจบสำเร็จ โปรแกรมตรวจหา SignTool และสร้างหรือใช้ใบรับรองทดสอบเดิม พร้อมเติม thumbprint

ปุ่มนี้รับตัวติดตั้ง EXE ที่ Windows ตรวจลายเซ็น Microsoft ได้เท่านั้น ไม่ดาวน์โหลดหรือรันไฟล์จากแหล่งอื่นให้อัตโนมัติ
ถ้ายกเลิกหรือติดตั้งไม่ครบ โปรแกรมจะแจ้งปัญหา ไม่รายงานว่า SignTool พร้อมใช้งาน
ระหว่าง SDK installer เปิดอยู่ ต้องปิดหรือยกเลิกจากตัว installer เอง ปุ่ม Stop ของโปรแกรมจะปิดไว้

## ใช้ใบรับรองทดสอบ
เลือกโหมด **Self-signed test / ใบรับรองทดสอบ** ใส่ชื่อผู้พัฒนา แล้วกด **สร้าง / ใช้ใบรับรองทดสอบเดิม**
ใช้ชื่อที่ไม่มีเครื่องหมาย , = + < > ; " หรือ backslash เพื่อสร้าง Subject ของใบรับรอง
โปรแกรมสร้าง RSA 3072-bit / SHA256 / Code Signing อายุ 2 ปี โดยใช้ private key แบบ NonExportable
ใบเดิมที่โปรแกรมสร้างและเหลืออายุเกิน 30 วันจะถูกใช้ซ้ำ ไม่สร้างใหม่ทุกครั้ง
ใบใกล้หมดอายุจะสร้างใบใหม่โดยเก็บใบเดิมไว้ ไม่ลบ key เดิม

Private key อยู่ใน **Cert:\CurrentUser\My** ของผู้ใช้ที่ติดตั้งหรือเปิด EXE Builder Studio
ไฟล์ CER สาธารณะและข้อมูล thumbprint อยู่ที่:
`%LOCALAPPDATA%\ExeBuilderStudio\certificates`
ไม่มี private key, PFX หรือรหัสผ่านถูกฝังใน ZIP / EXE / Setup และไม่มีการเพิ่มใบรับรองใน Trusted Root อัตโนมัติ
โปรแกรมที่นำมาสร้างตัวติดตั้ง เช่น AnimalDiceGame จะไม่สร้างใบรับรองให้เครื่องลูกค้า
ขั้นตอนสร้างใบรับรองหลังติดตั้งในไฟล์ installer/ExeBuilderStudio.iss ใช้สำหรับตัว EXE Builder Studio เท่านั้น

**ใบรับรองสร้างเองใช้ทดสอบ ไม่ใช่ใบรับรองสำหรับเผยแพร่ที่ Windows ทั่วไปเชื่อถือ**
การลงนามสำเร็จไม่รับรองว่า SmartScreen หรือ Smart App Control จะยอมให้เปิดโปรแกรม
การตรวจ `/pa` ของ SignTool มักไม่ผ่านสำหรับใบรับรองสร้างเอง เพราะไม่มีสายความเชื่อถือ ไม่ได้หมายความว่าไฟล์ไม่มีลายเซ็น
โปรแกรมแสดงสถานะ “ลงนามแล้ว แต่ยังไม่ตรวจความเชื่อถือ” จนกดตรวจและตรวจผ่านบนเครื่องนี้

## ใช้ใบรับรองสำหรับเผยแพร่
หากมีใบรับรอง Code Signing ที่ใช้ได้ ให้ติดตั้งตามคู่มือผู้ให้บริการ
- แบบ PFX: เลือก PFX/P12 ใส่รหัสผ่าน กดนำเข้า โปรแกรมตรวจ Code Signing / private key / อายุใบรับรอง
- แบบ Windows store หรือ USB token: เลือก CurrentUser\My หรือ LocalMachine\My แล้วกดเลือกใบรับรอง
  ต้องติดตั้ง driver/provider ของ token ตามคู่มือผู้ให้บริการ และ provider ต้องรองรับ SignTool
- ระบบลงนามบนคลาวด์ที่ต้องใช้ plugin หรือคำสั่งเฉพาะยังไม่ได้รองรับ

รหัสผ่าน PFX จะถูกส่งผ่าน stdin ไป PowerShell ไม่ถูกเขียนใน command line, Log, settings หรือไฟล์ชั่วคราว
PFX ต้นฉบับและ key ของคุณต้องเก็บแยกจาก release ที่นำมาสร้าง Setup ไม่เลือกโฟลเดอร์ที่มีไฟล์เหล่านี้

## ลงนามและประทับเวลา
1. ตรวจช่อง SignTool และ thumbprint เลือก store ให้ตรงกับใบรับรอง
2. ใส่ timestamp URL RFC 3161 ของผู้ให้บริการ เช่น `http://timestamp.digicert.com` หากต้องการ (ต้องต่ออินเทอร์เน็ต)
3. เลือกไฟล์แล้วกดลงนาม จากนั้นกดตรวจลายเซ็นและความเชื่อถือ
   การลงนามแก้ไขไฟล์ที่เลือกโดยตรง ควรเก็บไฟล์ต้นฉบับหากต้องการกลับไปก่อนลงนาม

เปิด **ลงนาม EXE และ Setup หลังสร้าง** เพื่อใช้กับงานต่อไป:
- Java: Launch4j สร้าง EXE → SignTool ลงนาม EXE
- Python: PyInstaller สร้าง EXE → SignTool ลงนาม EXE หลัก ทั้ง onefile และ onedir
- Installer: ลงนาม EXE หลักใน release → Inno Setup สร้าง Setup → ลงนาม Setup
ถ้าขั้นใดล้มเหลวจะหยุด ไม่ทำขั้นต่อไป และแจ้งใน Log
DLL/EXE อื่นใน release และ uninstaller ไม่ถูกลงนามอัตโนมัติในรุ่นนี้
หาก SignTool รายงานปัญหาประทับเวลา โปรแกรมจะไม่รายงานว่าขั้นลงนามสำเร็จ (ไม่ถอยไปลงนามแบบไม่มี timestamp เงียบ ๆ)

## สร้างตัวติดตั้งของ EXE Builder Studio
ต้องทำบน Windows ที่ติดตั้ง Python และ Inno Setup:

```powershell
cd E:\App\ExeBuilderStudio
powershell -ExecutionPolicy Bypass -File .\Build_Studio.ps1 -CreateInstaller
```

หากหา Inno Setup ไม่เจอ:

```powershell
powershell -ExecutionPolicy Bypass -File .\Build_Studio.ps1 -CreateInstaller -ISCC 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
```

ได้ `installer_output\ExeBuilderStudio_Setup.exe` รุ่น `AppVersion=1.0`
หลังติดตั้งจะสร้างใบรับรองทดสอบของผู้ใช้เครื่องนั้นอัตโนมัติ แม้ยังไม่ได้เปิดโปรแกรม
Windows SDK ไม่รวมมากับ Setup ต้องติดตั้งแยกสำหรับใช้ SignTool
ตัว Setup ของ Studio เองยังไม่ลงนามจาก Build_Studio.ps1 ให้นำไปลงนามด้วยใบรับรองของผู้เผยแพร่ก่อนแจก
ถ้าต้องสร้างใบรับรองโดยไม่เปิด GUI:

```powershell
powershell -ExecutionPolicy Bypass -File .\Ensure-Certificate.ps1 -Publisher 'Khurkham'
```

## การตรวจสอบ
มี tests/test_signing.py ตรวจคำสั่ง SignTool, timestamp, การค้นหา SDK และการแปลผล certificate command
ทดสอบบน Windows ด้วย tests/Windows_Smoke.ps1 เพื่อสร้างใบรับรองทดสอบ ตรวจการใช้ซ้ำ และลงนามสำเนา EXE
สคริปต์ Windows จะไม่ลงนามไฟล์ระบบต้นฉบับและไม่เพิ่ม Trusted Root
ชุดนี้เขียนและตรวจโค้ดใน Linux ยังไม่ได้ยืนยันการติดตั้ง Windows SDK, Inno Setup และ certificate store บน Windows จริง

อ้างอิง Microsoft:
- https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
- https://learn.microsoft.com/en-us/powershell/module/pki/new-selfsignedcertificate
