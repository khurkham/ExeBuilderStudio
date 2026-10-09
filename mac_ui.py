"""Mac build page, sharing the existing guarded QProcess lifecycle."""
import sys, shutil
from pathlib import Path
from PySide6.QtWidgets import QLabel,QComboBox,QFileDialog,QPushButton,QProgressBar
from PySide6.QtCore import QProcess,QProcessEnvironment
import mac_backend as mac

LABELS={
'mac':('macOS APP / DMG','macOS APP / DMG','macOS APP / DMG'),
'macpython':('Python → APP','Python → APP','Python → APP'),
'macjava':('Java → APP','Java → APP','Java → APP'),
'macdmg':('APP → DMG','APP → DMG','APP → DMG'),
'macicon':('Convert logo → ICNS','แปลงโลโก้ → ICNS','လူဝ်ႇၵူဝ်ႇ → ICNS'),
'macicns':('Mac icon (.icns)','ไอคอน Mac (.icns)','Mac icon (.icns)'),
'identifier':('Bundle ID','รหัส Bundle ID','Bundle ID'),
'architecture':('Architecture','สถาปัตยกรรม','Architecture'),
'identity':('Apple signing identity (optional)','ชื่อใบรับรอง Apple (ไม่บังคับ)','Apple signing identity'),
'jarfolder':('JAR folder + dependencies','โฟลเดอร์ JAR และไลบรารี','JAR / libraries folder'),
'jarname':('JAR filename','ชื่อไฟล์ JAR','JAR filename'),
'mainclass':('Main class (optional)','Main class (ไม่บังคับ)','Main class'),
'appbundle':('APP bundle to package','เลือก APP เพื่อสร้าง DMG','APP bundle'),
'macnote':('Build on a Mac. APP uses onedir/windowed. Native architecture follows the selected Python/JDK. DMG contains the APP and an Applications shortcut. This trial does not notarize apps.', 'ต้องสร้างบน Mac: APP ใช้ onedir/windowed สถาปัตยกรรม Native ตาม Python/JDK ที่เลือก DMG มีแอปและทางลัด Applications รุ่นทดลองยังไม่ส่ง notarization ให้ Apple', 'သၢင်ႈ APP / DMG ၼိူဝ် macOS။ Native architecture: Python / JDK။ Apple notarization ဢမ်ႇပႆႇမီး။'),
'mactools':('Check Mac tools','ตรวจเครื่องมือ Mac','ၵူတ်ႇ Mac tools'),
}

def add_mac_page(host,translations):
    translations.update(LABELS)
    note=QLabel();note.setWordWrap(True);host.labels.append((note,'macnote'));host.pages['mac'].addRow(note)
    for key,kind,default in [('Python interpreter','file',sys.executable if not getattr(sys,'frozen',False) else (shutil.which('python3') or '')),('source','file',''),('output','dir',''),('name',None,'MyApplication'),('identifier',None,'com.khurkham.myapp'),('icon','icns',''),('data','dir',''),('hidden',None,''),('identity',None,'')]:host.field('mac',key,kind,default)
    # The shared icon label says ICO on Windows; this row specifically accepts ICNS.
    for n,(widget,key) in enumerate(host.labels):
        if key=='icon' and widget is host.pages['mac'].labelForField(host.fields['mac/icon'].parentWidget()):host.labels[n]=(widget,'macicns')
    host.macarch=QComboBox();host.macarch.addItems(['native','arm64','x86_64','universal2']);label=QLabel();host.labels.append((label,'architecture'));host.pages['mac'].addRow(label,host.macarch)
    host.button('mac','macpython',lambda:build_python(host))
    for key,kind,default in [('jpackage','file',shutil.which('jpackage') or ''),('jarfolder','dir',''),('jarname',None,'app.jar'),('mainclass',None,''),('version',None,'1.0.0'),('jre','dir','')]:host.field('mac',key,kind,default)
    host.button('mac','macjava',lambda:build_java(host))
    host.field('mac','appbundle',kind='dir');host.button('mac','macdmg',lambda:build_dmg(host))
    host.field('mac','logo',kind='image');host.button('mac','macicon',lambda:convert_icon(host))
    host.button('mac','mactools',lambda:check_tools(host))
    host.build_progress=QProgressBar();host.build_progress.setRange(0,1);host.build_progress.setValue(0);host.pages['mac'].addRow(host.build_progress)

def run_plan(host,plan):
    tool,args,cwd,target=plan;host.last_output=str(target.parent)
    def done(output):
        mac.require_app(target);host.fields['mac/appbundle'].setText(str(target));host.log.appendPlainText('APP created: '+str(target))
    host.start(tool,args,cwd,callback=done,label='Building macOS APP…')

def build_python(h):
    v=lambda k:h.v('mac',k)
    run_plan(h,mac.python_plan(v('Python interpreter'),v('source'),v('output'),v('name'),v('identifier'),v('icon'),v('data'),v('hidden'),h.macarch.currentText(),v('identity')))

def build_java(h):
    v=lambda k:h.v('mac',k)
    if v('identity'):raise ValueError('Java APP signing is not implemented in this trial. Clear Apple signing identity before building Java.')
    run_plan(h,mac.java_plan(v('jpackage'),v('jarfolder'),v('jarname'),v('output'),v('name'),v('identifier'),v('version'),v('mainclass'),v('icon'),v('jre')))

def build_dmg(h):
    mac.require_mac();app=mac.require_app(h.v('mac','appbundle'));name=h.v('mac','name');mac.safe_name(name)
    out=mac.fresh_output(h.v('mac','output'),name+'.dmg')
    if out==app or app in out.parents:raise ValueError('Output must be outside the APP')
    # The frozen application can run a dedicated helper mode without an external Python.
    if getattr(sys,'frozen',False):tool=sys.executable;args=['--ebs-dmg',str(app),str(out),name]
    else:tool=sys.executable;args=[str(Path(__file__).with_name('mac_backend.py')),str(app),str(out),name]
    h.last_output=str(out)
    def done(output):
        if not (out/(name+'.dmg')).is_file():raise ValueError('DMG output is missing')
        h.log.appendPlainText('DMG created: '+str(out/(name+'.dmg')))
    h.start(tool,args,callback=done,label='Building DMG…')

def convert_icon(h):
    out=h.output('mac');name=mac.safe_name(h.v('mac','name'));target=out/(name+'.icns')
    if target.exists():raise ValueError('ICNS exists. Choose a new name.')
    mac.convert_icns(h.v('mac','logo'),target);h.fields['mac/icon'].setText(str(target));h.log.appendPlainText(str(target))

def check_tools(h):
    mac.require_mac()
    for key in ['Python interpreter','jpackage']:
        p=h.v('mac',key)
        try:mac.executable(p);h.log.appendPlainText(key+': '+p)
        except ValueError as e:h.log.appendPlainText(str(e))
    for key in ['hdiutil','codesign','security','xcrun']:h.log.appendPlainText(key+': '+(shutil.which(key) or 'Not installed'))
    python=mac.executable(h.v('mac','Python interpreter'))
    h.start(python,['-c','import sys,platform,PyInstaller; print("Python:",sys.version); print("Architecture:",platform.machine()); print("PyInstaller:",PyInstaller.__version__)'],label='Checking Python / PyInstaller…')
